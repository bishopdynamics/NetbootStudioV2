#!/usr/bin/env bash
# Deploy all Netboot Studio containers and config

source nscommon.bashlib || {
  echo "failed to source nscommon.bashlib"
  exit 1
}
function bail() {
  echo "Error: $*"
  exit 1
}

announce "Deploying Netboot Studio"

takenote "lets check some flags"
check_flag_set "first_time_setup_failed" && bail "first_time_setup_failed flag exists, you need to start over with a fresh Debian 11 installation. Contact Support."
check_flag_set "first_time_setup_complete" || bail "need to run: ./first_time_setup.sh (and reboot) first"
if [ ! -f "local_environment.sh" ]; then
  echo "missing local_environment.sh, but first_time_setup_complete flag exists, so something is wrong. Contact Support."
  exit 1
fi
source "local_environment.sh"

takenote "and how are those certs doing?"
check_certs || exit 1

######## global vars

REBUILD_IMAGE="True"  # for now, we always rebuild the image
SUDO_FOLDERS="/opt/local"
REGULAR_FOLDERS_A=" /opt/local/database /opt/local/broker /opt/local/broker/config /opt/local/nfs"
REGULAR_FOLDERS_B="/opt/NetbootStudio/boot_images /opt/NetbootStudio/certs /opt/NetbootStudio/unattended_configs"
REGULAR_FOLDERS_C="/opt/NetbootStudio/stage1_files /opt/NetbootStudio/stage4 /opt/NetbootStudio/uboot_scripts"
REGULAR_FOLDERS_D="/opt/NetbootStudio/ipxe_builds /opt/NetbootStudio/wimboot_builds"
REGULAR_FOLDERS_E="/opt/NetbootStudio/uboot_binaries /opt/NetbootStudio/packages /opt/NetbootStudio/tftp_root /opt/NetbootStudio/iso"

####### helper functions

function chown_folder() {
  # chown a folder as the current user
  local folder="$1"
  echo "may need to sudo to chown folder: $folder as user ${GIVEN_NON_ROOT_USERNAME}"
  sudo chown -R "${GIVEN_NON_ROOT_USERNAME}" "$folder" || bail "failed to chown folder $folder as user ${GIVEN_NON_ROOT_USERNAME}"
}

function create_folder() {
  # create a folder
  local folder="$1"
  echo "creating $folder"
  mkdir -p "$folder" || bail "failed to create folder: $folder"
}

function create_folder_sudo() {
  # create a folder that we need sudo to do (then chown it as us)
  local folder="$1"
  echo "may need to sudo to create folder: $folder"
  sudo mkdir -p "$folder" || bail "failed to create folder: $1"
  chown_folder "$folder"
}

function check_folder() {
  # check for the existence of a folder, and make it if needed
  #   presumes we do NOT need sudo
  local folder="$1"
  echo "checking folder: $folder"
  if [ ! -d "$folder" ]; then
    create_folder "$folder"
  fi
}

function check_folder_sudo() {
  # check for the existence of a folder, and make it if needed
  #   presumes we need sudo, and will chown folder if it exists
  local folder="$1"
  echo "checking folder (sudo): $folder"
  if [ ! -d "$folder" ]; then
    create_folder_sudo "$folder"
  else
    chown_folder "$folder"
  fi
}

function check_all_folders() {
  echo "Checking for and creating folders as needed"
  for this_folder in $SUDO_FOLDERS; do
    check_folder_sudo "$this_folder"
  done
  for this_folder in $REGULAR_FOLDERS_A; do
    check_folder "$this_folder"
  done
  for this_folder in $REGULAR_FOLDERS_B; do
    check_folder "$this_folder"
  done
  for this_folder in $REGULAR_FOLDERS_C; do
    check_folder "$this_folder"
  done
  for this_folder in $REGULAR_FOLDERS_D; do
    check_folder "$this_folder"
  done
  for this_folder in $REGULAR_FOLDERS_E; do
    check_folder "$this_folder"
  done
}

function check_config_file() {
  echo "checking config file"
  if [ ! -f /opt/NetbootStudio/config.ini ]; then
    bail "Did not find config.ini, first_time_setup failed. Contact Support."
  fi
}

function rebuild_image() {
  # rebuild the image from source
  echo "Rebuilding image..."
  mkdir -p ./tmp || bail "failed to create folder: ./tmp"
  # shellcheck disable=SC2002
  echo "$(cat "VERSION" | tr -d '\n' |tr -d '\r')-$(git rev-parse --short HEAD)-$(uname)-$(uname -m)" > ./tmp/VERSION
  docker build -t bishopdynamics/netbootstudio . || bail "failed to build docker image"
  rm -r ./tmp || bail "failed to clean up folder: ./tmp"
}

##### Start work here

takenote "lets check those folders too"
check_all_folders
takenote "and the config.ini, did that get created?"
check_config_file

takenote "lets stop any containers if they are running"
./stop.sh || bail "failed to stop existing containers"

takenote "wow thats... kinda surprising actually. lets build it shall we?"

if [ "$REBUILD_IMAGE" == "True" ]; then
  rebuild_image
fi

takenote "AW YEAH! That was aweSOME! I love building things"
takenote "ok find you can have your containers now"
echo "Bringing up containers..."
docker-compose up -d || bail "failed to bring up containers"

takenote "and lets start up that nfs server"
sudo systemctl start nfs-kernel-server || {
  echo "failed to start nfs-kernel-server. most of Netboot Studio will work fine, except for boot images that use nfs"
  echo " you should still look into why nfs-kernel server failed to start, and report this issue to Support"
}

echo ""
echo " Success! You can access the WebUI at: https://$(hostname)/"
echo "   services may take up to 20 seconds to be available"
echo "   to monitor logs, run: ./monitor.sh"
echo ""

exit 0
