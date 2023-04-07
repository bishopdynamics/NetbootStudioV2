#!/usr/bin/env bash

# NOTE this script has sections with heredocs that are not indented to match the function indentation level
# TODO - check for required commands properly and early


# build a liveimage

BUILD_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S %z')

CONFIG_ARCH="$1"
DISTRO="$2"
WITH_GUI="$3"

DO_BUILD="True"
CURRENT_DIR=$(pwd)

if [ -z "$CONFIG_ARCH" ] || [ -z "$DISTRO" ] || [ -z "$WITH_GUI" ]; then
	echo ""
	echo "need to provide arch: amd64 or arm64"
	echo "need to provide the distro: bullseye or buster"
	echo "need to provide image type: gui or nogui"
	echo " usage: ${0} \"amd64\" \"bullseye\" \"gui\""
	echo " usage: ${0} \"arm64\" \"buster\" \"nogui\""
	echo ""
	echo "invalid arguments"
	exit 1
fi

# the WITH_GUI option can only be "gui" or "nogui"
if [ "$WITH_GUI" != "gui" ]; then
	WITH_GUI="nogui"
fi

# must be root
if [ "$(id -u)" -gt 0 ]; then
	echo "need to run as root"
	exit 1
fi

BOOT_IMAGE_NAME="LiveImage-Debian-${DISTRO}-${CONFIG_ARCH}-${WITH_GUI}"

STAGING_FOLDER="${CURRENT_DIR}/${BOOT_IMAGE_NAME}-staging"
FINAL_IMAGE_FOLDER="${CURRENT_DIR}/${BOOT_IMAGE_NAME}"

function cleanup_staging() {
	echo "cleaning up staging folder"
	if [ -d "${STAGING_FOLDER}" ]; then
		# if it failed previously, stuff could be mounted in there
		# shellcheck disable=SC2086 # we need the glob
		umount -r ${STAGING_FOLDER}/* 2>/dev/null  # there will be errors, hide them
		# now removal should work fine
		rm -r "${STAGING_FOLDER}" || {
			echo "failed to clean up staging build folder"
			exit 1
		}
	fi
}

function bail () {
	echo " build-image ERROR: $*"
	exit 1
}

#############################  Start of config_image  #############################

function config_image () {
	local CONFIG_ARCH="$1"
	local OUTPUT_DIR="$2"
	local CONFIG_DIST="$3"  # bullseye / buster


	local CONFIG_MODE="debian"
	local CONFIG_FLAVOR="$CONFIG_ARCH"  # for our cases it always follows arch
	local CONFIG_IMAGE="netboot"
	local CONFIG_MIRROR="http://deb.debian.org/debian/"
	local CONFIG_FSTYPE="squashfs"

	local HOST_ARCH
	HOST_ARCH=$(dpkg --print-architecture)
	if [ "$HOST_ARCH" == "arm64" ] || [ "$HOST_ARCH" == "amd64" ]; then
		echo "Host arch is supported: $HOST_ARCH"
	else
		echo "Unsupported host arch: $HOST_ARCH"
		exit 1
	fi

	echo "######## config-image ################"

	if [ -z "$CONFIG_ARCH" ] || [ -z "$OUTPUT_DIR" ] || [ -z "$CONFIG_DIST" ]; then
		echo "config_image got wrong args, this indicates bug with the script"
		exit 1
	fi

	if [ "$CONFIG_ARCH" == "arm64" ] || [ "$CONFIG_ARCH" == "amd64" ]; then
		echo "Target arch is supported: $CONFIG_ARCH"
	else
		bail "Unsupported target arch: $CONFIG_ARCH"
	fi

	if [ "$CONFIG_DIST" == "buster" ] || [ "$CONFIG_DIST" == "bullseye" ]; then
		echo "Target distro is supported: $CONFIG_DIST"
	else
		bail "Unsupported target distro: $CONFIG_DIST"
	fi

	# check for lb
	command -v lb || {
		echo ""
		echo "cannot find the command: lb, you need to install live-build via apt"
		echo " try: sudo apt-get install -y gcc-aarch64-linux-gnu qemu qemu-system live-build qemu-user-static"
		echo ""
		bail "missing prereqs"
		# echo "going to try to install it via apt"
		# apt-get install -y live-build || bail "failed to install live-build via apt"
	}

	# setup a clean output dir
	echo "output dir: $OUTPUT_DIR"
	if [ -d "$OUTPUT_DIR" ]; then
		bail "existing OUTPUT_DIR: $OUTPUT_DIR"
	fi

	mkdir "$OUTPUT_DIR" || bail "failed to make dir: $OUTPUT_DIR"
	pushd "$OUTPUT_DIR" || bail "failed to pushd to dir: $OUTPUT_DIR"

	# create a neat auto config
	echo "running config"
	mkdir auto
	cp /usr/share/doc/live-build/examples/auto/* auto/

	# vars will expand at time of file creation
	cat <<EOF > auto/config
#!/bin/sh

lb config noauto \\
	--mode "$CONFIG_MODE" \\
	--distribution "$CONFIG_DIST" \\
	--architectures "$CONFIG_ARCH" \\
	--linux-flavours "$CONFIG_FLAVOR" \\
	--binary-images "$CONFIG_IMAGE" \\
	--mirror-binary "$CONFIG_MIRROR" \\
	--chroot-filesystem "$CONFIG_FSTYPE" \\
EOF

	# 	--bootstrap-qemu-static "/usr/bin/qemu-aarch64-static" \

	if [ "$CONFIG_ARCH" == "arm64" ] && [ "$HOST_ARCH" == "amd64" ]; then
		echo "looks like we are building using qemu-aarch64-static today"
		cat << 'EOF_QEMU_ARM' >> auto/config
	--bootstrap-qemu-arch "arm64" \
	--bootstrap-qemu-static "/usr/bin/qemu-aarch64-static" \
EOF_QEMU_ARM
	fi

	if [ "$CONFIG_ARCH" == "amd64" ] && [ "$HOST_ARCH" == "arm64" ]; then
		echo "looks like we are building using qemu-x86_64-static today"
		cat << 'EOF_QEMU_AMD' >> auto/config
	--bootstrap-qemu-arch "amd64" \
	--bootstrap-qemu-static "/usr/bin/qemu-x86_64-static" \
EOF_QEMU_AMD
	fi

	# the trailer needs to NOT expand variables
	cat << 'EOF_TRAILER' >> auto/config
	"${@}"

EOF_TRAILER

	lb config || bail "lb config failed"

	mkdir chroot
	mkdir tftpboot

	popd || bail "failed to popd"

	echo "######## done with config-image #############"
}

#############################  End of config_image  #############################


if [ "$DO_BUILD" == "True" ]; then
	echo "############### preparing folders and config #############"
	echo ""

	cleanup_staging

	config_image "$CONFIG_ARCH" "$STAGING_FOLDER" "$DISTRO" || bail "failed to config_image $CONFIG_ARCH $STAGING_FOLDER $DISTRO"

	cd "$STAGING_FOLDER" || bail "failed to cd to STAGING_FOLDER"

	echo "htop fdisk parted u-boot-tools nfs-common xfsprogs lm-sensors hfsplus hfsutils iotop iftop pv wget curl file" >> config/package-lists/my.list.chroot
	if [ "$WITH_GUI" == "gui" ]; then
		echo "task-xfce-desktop firefox-esr gparted " >> config/package-lists/my.list.chroot
	fi

	echo "################# building the liveimage  ###############"
	# Do the build
	echo "running build"

	lb build 2>&1 | tee build.log || bail "lb build failed"
fi


echo "################# creating a valid Netboot Studio boot image  ###############"

KERNEL_NAME="vmlinuz"
INITRD_NAME="initrd.img"
SQUASHFS_NAME="filesystem.squashfs"
KERNEL_ARGS=""

# verify the build actually produced all the files (aka succeeded)
if [ ! -f "${STAGING_FOLDER}/binary/live/${SQUASHFS_NAME}" ]; then
	bail "unable to find results of build: ${SQUASHFS_NAME}, presuming build failed"
fi

if [ -d "$FINAL_IMAGE_FOLDER" ]; then
	echo "removing existing FINAL_IMAGE_FOLDER: $FINAL_IMAGE_FOLDER"
	rm -r "$FINAL_IMAGE_FOLDER" || bail "could not delete existing FINAL_IMAGE_FOLDER"
fi
mkdir "$FINAL_IMAGE_FOLDER" || bail "could not create FINAL_IMAGE_FOLDER"

echo "writing stage2.ipxe"

cat << 'EOF' > "${FINAL_IMAGE_FOLDER}/stage2.ipxe"
set live-kernel-args initrd=initrd.img boot=live config hooks=filesystem username=live noeject fetch=${boot-image-path}/filesystem.squashfs
set extra-kernel-args ipv6.disable=1 IPV6_DISABLE=1 console=tty1 console=ttyS2,1500000
imgfree
imgfetch ${boot-image-path}/vmlinuz || goto failed
imgfetch ${boot-image-path}/initrd.img || goto failed
imgload vmlinuz || goto failed
imgargs vmlinuz ${live-kernel-args} -- ${extra-kernel-args} || goto failed
imgexec || goto failed
EOF

cat << EOF > "${FINAL_IMAGE_FOLDER}/metadata.yaml"
created: "${BUILD_TIMESTAMP}"
image_type: "debian-liveimage"
description: "auto-built using debian-liveimage, debian ${DISTRO} ${CONFIG_ARCH} ${WITH_GUI}"
release: "${DISTRO}"
arch: "${CONFIG_ARCH}"
stage2_filename: "stage2.ipxe"
supports_unattended: "false"
stage2_unattended_filename: "none"
EOF

echo "grabbing ${KERNEL_NAME}, ${INITRD_NAME}, ${SQUASHFS_NAME}"
# the glob business below is needed because arm64 builds end up with a whole kernel version appended, while amd64 builds are just bare named
pushd "${STAGING_FOLDER}/tftpboot/live/" || bail "failed to pushd ${STAGING_FOLDER}/tftpboot/live/"
if [ ! -f "${KERNEL_NAME}" ]; then
	mv ${KERNEL_NAME}* ${KERNEL_NAME} || bail "failed to rename file with version appended"
fi
if [ ! -f "${INITRD_NAME}" ]; then
	mv ${INITRD_NAME}* ${INITRD_NAME} || bail "failed to rename file with version appended"
fi
popd || bail "somehow popd failed"


mv "${STAGING_FOLDER}/tftpboot/live/${KERNEL_NAME}" "${FINAL_IMAGE_FOLDER}/${KERNEL_NAME}" || bail "failed to move output files to final boot image folder"
mv "${STAGING_FOLDER}/tftpboot/live/${INITRD_NAME}" "${FINAL_IMAGE_FOLDER}/${INITRD_NAME}" || bail "failed to move output files to final boot image folder"
mv "${STAGING_FOLDER}/binary/live/${SQUASHFS_NAME}" "${FINAL_IMAGE_FOLDER}/" || bail "failed to move output files to final boot image folder"

cleanup_staging

echo ""
echo "Success! image is at ${FINAL_IMAGE_FOLDER}, you should put it in /opt/NetbootStudio/boot_images/"
