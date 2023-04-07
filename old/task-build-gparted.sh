#!/bin/bash

# this is the old way we did things, for reference only

########################### vars populated by runner
OPT_NAME="%s"
OPT_ISO="%s"
OPT_KERNEL_ARGUMENTS="%s"
OPT_IMAGE_TYPE="%s"
IMAGES_FOLDER="%s"
ISO_FOLDER="%s"
PROGRESS_FILE="%s"

function status {
    echo "$1" > ${PROGRESS_FILE}
}


############################################## vars calculated at runtime
TIMESTAMP=$(date '+%%Y-%%m-%%d_%%H:%%M:%%S')
DEST_FOLDER="${IMAGES_FOLDER}/${OPT_NAME}"
SCRIPT_FULL_PATH="${DEST_FOLDER}/netboot.ipxe"
# SCRIPT_UNATTENDED_FULL_PATH="${DEST_FOLDER}/netboot-unattended.ipxe"
METADATA_FULL_PATH="${DEST_FOLDER}/metadata.yaml"
ISO_FILE="${ISO_FOLDER}/${OPT_ISO}"

mkdir -p "$DEST_FOLDER"
status 15

############################################## Extract ISO

7z x -o"$DEST_FOLDER" "$ISO_FILE"

pushd "$DEST_FOLDER" || exit
find . -type d -exec chmod a+rx {} \;
popd || exit

##################################################################### create netboot.ipxe
status 80
echo "Generating ipxe boot script: $SCRIPT_FULL_PATH"

# header, resolve variables now
cat << END_HEAD > "$SCRIPT_FULL_PATH"
#!ipxe
# Auto-Generated ipxe script for ${OPT_IMAGE_TYPE}
# Image: ${DEST_FOLDER}
# Source ISO: ${ISO_FILE}
# Created: ${TIMESTAMP}
# Image Type: ${OPT_IMAGE_TYPE}
# Unattended: False

set image-name ${OPT_NAME}
set extra-kernel-args ${OPT_KERNEL_ARGUMENTS}

END_HEAD

status 85

# body, dont resolve any variables
cat << 'END_BODY' >> "$SCRIPT_FULL_PATH"

set http-server http://${next-server}
set images-root ${http-server}/images

set this-image-base ${images-root}/${image-name}/live
set this-image-kernel vmlinuz
set this-image-initrd initrd.img
set this-image-args initrd=initrd.img boot=live config components union=overlay username=user noswap noeject ip= vga=788 fetch=${this-image-base}/filesystem.squashfs --- ${extra-kernel-args}
show this-image-base
show this-image-kernel
show this-image-initrd
set this-full-kernel-uri ${this-image-base}/${this-image-kernel}
set this-full-initrd-uri ${this-image-base}/${this-image-initrd}
echo xxxxxxxxxxx  starting xxxxxxxxxxx
imgfree
imgfetch ${this-full-kernel-uri} || goto boot-failed
imgfetch ${this-full-initrd-uri} || goto boot-failed
imgload ${this-image-kernel} || goto boot-failed
imgargs ${this-image-kernel} ${this-image-args} || goto boot-failed
imgexec || goto boot-failed


:failed
echo Something failed, hopefully errors are printed above this
prompt Press any key to reboot
goto reboot

:boot-failed
echo Failed to boot! hopefully errors are printed above this
echo   make sure that you use the correct architecture
prompt Press any key to reboot
goto reboot

:reboot
reboot

END_BODY


############################################## create metadata.yaml
status 75
echo "Generating metadata.yaml"

cat << END_M >> "$METADATA_FULL_PATH"
created: "${TIMESTAMP}"
image_type: ${OPT_IMAGE_TYPE}
description: "Auto-Generated image for ${OPT_IMAGE_TYPE}"
END_M


############################################## Done
echo "done generating image"
status 100

# (input_data['name'], input_data['iso'], input_data['kernel_arguments'], input_data['image_type'], IMAGES_FOLDER, ISO_FOLDER, progress_file)

