#!/bin/bash
########################### vars populated by runner
OPT_NAME="%s"
OPT_ISO="%s"
OPT_CREATE_UNATTENDED="%s"
OPT_IMAGE_TYPE="%s"
IMAGES_FOLDER="%s"
ISO_FOLDER="%s"
PROGRESS_FILE="%s"

function status {
    echo "$1" > ${PROGRESS_FILE}
}

function status_fail {
    echo " [ FAIL ]"
    exit 1
}

function do_cmd {
    local COMMAND
    COMMAND="$@"
    echo "${COMMON_PREFIX} Running command: $COMMAND"
    $COMMAND || status_fail
    echo "${COMMON_PREFIX} Done"
}

ISO_FILE="${ISO_FOLDER}/${OPT_ISO}"
IMAGE_NAME="$OPT_NAME"

STORAGE_SERVER="192.168.1.188"
PERMS_USER="james"
PERMS_GROUP="dialout"

# various root folders
IMAGES_FOLDER="/opt/tftp-root/images"
# have to escape both \\ chars at beginning
SMB_FOLDER="\\\\\\\\${STORAGE_SERVER}\\netboot\\images"
FULL_SMB_PATH="${SMB_FOLDER}\\\\${IMAGE_NAME}"

TIMESTAMP=$(date '+%%Y-%%m-%%d_%%H:%%M:%%S')
DEST_FOLDER="${IMAGES_FOLDER}/${IMAGE_NAME}"
SCRIPT_FULL_PATH="${DEST_FOLDER}/netboot.ipxe"
SCRIPT_UNATTENDED_FULL_PATH="${DEST_FOLDER}/netboot-unattended.ipxe"

METADATA_FULL_PATH="${DEST_FOLDER}/metadata.yaml"


if [ -d "$DEST_FOLDER" ]; then
    # folder exists, no refresh flag
    echo "desination folder already exists, please delete it and try again"
    echo "folder: $DEST_FOLDER"
    exit 1
fi

echo "$TIMESTAMP - Preparing an image for netboot"

#################################### extract iso using 7z
echo "extracting [$ISO_FILE] to [$DEST_FOLDER]"
status 0
do_cmd mkdir -p "$DEST_FOLDER"
do_cmd 7z x -o"$DEST_FOLDER" "$ISO_FILE"


#################################### create mount.cmd and winpeshl.ini
echo "generating winpeshl.ini and mount.cmd"

# note that we call cmd.exe after mount.cmd, as a fallback shell in case something fails
# if startnet.cmd hangs and we close the window, then mount.cmd will fail and close, and then a prompt will appear
# if mount.cmd hangs and we close the window, then a prompt will appear
# if mount.cmd works as intended, cmd.exe never gets a chance to run

status 60

cat << 'END_WINPESHLINI' > "${DEST_FOLDER}/winpeshl.ini"
[LaunchApps]
"startnet.cmd"
"mount.cmd"
"cmd.exe"
END_WINPESHLINI

status 65

cat << END_STARTNETCMD > "${DEST_FOLDER}/startnet.cmd"
@echo off
echo if wpeinit fails, you will be dropped to a command prompt
echo this might take a minute...
@echo on
wpeinit
END_STARTNETCMD

status 70

cat << END_MOUNTCMD > "${DEST_FOLDER}/mount.cmd"
ipconfig
@echo off
echo
echo
echo if any of this fails, you will be dropped to a command prompt
echo this might take a minute...
@echo on
net use s: ${FULL_SMB_PATH} foo /user:foo\bar
@echo off
echo checking for unattend.xml
if exist x:\\windows\\system32\\unattend.xml (
    echo using x:\\windows\\system32\\unattend.xml
    echo this might take a minute...
    @echo on
    s:\\sources\\setup.exe /unattend:x:\\windows\\system32\\unattend.xml
) else (
    echo unattend.xml does not exist
    echo this might take a minute...    
    @echo on
    s:\\sources\\setup.exe
)

END_MOUNTCMD

#################################### Set permissions

status 75

echo "correcting file permissions"
# for windows installer to work, all dll & exe files need to be marked executable

pushd "$DEST_FOLDER"
# this is obnoxious, but without x nothing is reachable in apache
do_cmd find . -exec chmod a+rx {} \\;
popd
# make sure tftp-root has correct perms after all this
# TODO username and group are hardcoded
do_cmd sudo chmod 777 "$DEST_FOLDER"
do_cmd sudo chown -R ${PERMS_USER}:${PERMS_GROUP} "$DEST_FOLDER"


#################################### generate the ipxe script

status 80

echo "Generating ipxe boot script: $SCRIPT_FULL_PATH"

# header, resolve variables now
cat << END_HEAD > "$SCRIPT_FULL_PATH"
#!ipxe
# Auto-Generated ipxe script for windows installer
# Image: $DEST_FOLDER
# Source ISO: $ISO_FILE
# Created: $TIMESTAMP
# Image Type: $OPT_IMAGE_TYPE
# Unattended: False

set wim-image-name $IMAGE_NAME
END_HEAD

status 85

# body, dont resolve any variables
cat << 'END_BODY' >> "$SCRIPT_FULL_PATH"

set http-server http://${next-server}
set full-image-path ${http-server}/images/${wim-image-name}

imgload ${http-server}/wimboot || goto failed
imgfetch ${full-image-path}/boot/fonts/segmono_boot.ttf  segmono_boot.ttf ||
imgfetch ${full-image-path}/boot/fonts/segoe_slboot.ttf  segoe_slboot.ttf ||
imgfetch ${full-image-path}/boot/fonts/segoen_slboot.ttf segoen_slboot.ttf ||
imgfetch ${full-image-path}/boot/fonts/wgl4_boot.ttf     wgl4_boot.ttf ||
imgfetch ${full-image-path}/startnet.cmd startnet.cmd || goto failed
imgfetch ${full-image-path}/mount.cmd mount.cmd || goto failed
imgfetch ${full-image-path}/winpeshl.ini winpeshl.ini|| goto failed
imgfetch ${full-image-path}/boot/bcd BCD || goto failed
imgfetch ${full-image-path}/boot/boot.sdi boot.sdi || goto failed
imgfetch -n boot.wim ${full-image-path}/sources/boot.wim boot.wim || goto failed
imgexec || goto failed

:failed
echo Something failed, hopefully errors are printed above this
prompt Press any key to reboot
reboot
END_BODY


if [ "$OPT_CREATE_UNATTENDED" = "True" ]; then
#################################### generate the ipxe script for unattended

status 87

echo "Generating ipxe boot script: $SCRIPT_UNATTENDED_FULL_PATH"

# header, resolve variables now
cat << END_U_HEAD > "$SCRIPT_UNATTENDED_FULL_PATH"
#!ipxe
# Auto-Generated ipxe script for windows installer
# Image: $DEST_FOLDER
# Source ISO: $ISO_FILE
# Created: $TIMESTAMP
# Image Type: $OPT_IMAGE_TYPE
# Unattended: True

set wim-image-name $IMAGE_NAME
END_U_HEAD

# body, dont resolve any variables
cat << 'END_U_BODY' >> "$SCRIPT_UNATTENDED_FULL_PATH"

set http-server http://${next-server}
set full-image-path ${http-server}/images/${wim-image-name}

imgload ${http-server}/wimboot || goto failed
imgfetch ${full-image-path}/boot/fonts/segmono_boot.ttf  segmono_boot.ttf ||
imgfetch ${full-image-path}/boot/fonts/segoe_slboot.ttf  segoe_slboot.ttf ||
imgfetch ${full-image-path}/boot/fonts/segoen_slboot.ttf segoen_slboot.ttf ||
imgfetch ${full-image-path}/boot/fonts/wgl4_boot.ttf     wgl4_boot.ttf ||
imgfetch http://${next-server}:6161/unattend.xml?macaddress=${mac} unattend.xml || goto failed
imgfetch ${full-image-path}/startnet.cmd startnet.cmd || goto failed
imgfetch ${full-image-path}/mount.cmd mount.cmd || goto failed
imgfetch ${full-image-path}/winpeshl.ini winpeshl.ini|| goto failed
imgfetch ${full-image-path}/boot/bcd BCD || goto failed
imgfetch ${full-image-path}/boot/boot.sdi boot.sdi || goto failed
imgfetch -n boot.wim ${full-image-path}/sources/boot.wim boot.wim || goto failed
imgexec || goto failed

:failed
echo Something failed, hopefully errors are printed above this
prompt Press any key to reboot
reboot
END_U_BODY
fi

status 95
echo "Generating metadata.yaml"

cat << END_M >> "$METADATA_FULL_PATH"
source_iso: "${ISO_FILE}"
created: "${TIMESTAMP}"
image_type: "${OPT_IMAGE_TYPE}"
description: "Auto-Generated image for ${OPT_IMAGE_TYPE}"
END_M

status 100

echo "Done"