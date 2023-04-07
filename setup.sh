#!/usr/bin/env bash
# Netboot Studo setup script

# TODO make nfs and samba secure (no guest, only user netbootstudio)

# TODO why root doesnt have /usr/sbin in path?
PATH=/usr/sbin:$PATH

source ./bin/nscommon.bashlib || {
  echo "failed to source nscommon.bashlib"
  exit 1
}

# must be run as root
check_root

function bail () {
  set_flag first_time_setup_failed
  echo "Setup Failed!"
	echo " Error: $*"
	exit 1
}


./stop.sh 


check_flag_set "first_time_setup_complete" && bail "first_time_setup_complete flag exists, already ran first_time_setup.sh!"
check_flag_set "first_time_setup_failed" && bail "first_time_setup_failed flag exists, you need to start over with a fresh Debian 11 installation. Contact Support."



######################################################  Static Vars  ######################################################

# paths and users
NS_CONFIGDIR="/opt/NetbootStudio"
LOCAL_DIR="/opt/local"
SERVICE_USER="netboot"
SERVICE_GROUP="netboot"
WEBUI_ADMIN_USER="admin"

# packages
PKGS_PREREQS="python3-pip gcc make sed grep perl genisoimage liblzma-dev binutils unzip isolinux mtools u-boot-tools live-build nfs-common mosquitto-clients mosquitto nfs-kernel-server gnupg2 git curl whois"
PKGS_LDAP="python3-dev libldap2-dev libsasl2-dev ldap-utils tox lcov valgrind"
PKGS_QEMU="qemu-utils qemu-efi-aarch64 qemu-system-arm qemu-user-static"
PKGS_DOCKER="docker-ce docker-ce-cli containerd.io docker-compose"

announce "Netboot Studio Setup"

function generate_local_env () {
  takenote "generating local_environment.sh"
  cat << EOF_LOCAL_ENV > local_environment.sh
LOCAL_DIR="$LOCAL_DIR"
NS_CONFIGDIR="$NS_CONFIGDIR"
SERVICE_USER="$SERVICE_USER"
SERVICE_GROUP="$SERVICE_GROUP"
SERVICE_UID="$SERVICE_UID"
SERVICE_GID="$SERVICE_GID"
DB_PASSWORD="$DB_PASSWORD"
BROKER_PASSWORD="$BROKER_PASSWORD"
SAMBA_PASSWORD="$SAMBA_PASSWORD"
NFS_PASSWORD="$NFS_PASSWORD"
SERVER_HOSTNAME=$(hostname)
SERVER_IPADDRESS=$(get_ip_address)
WEBUI_ADMIN_USER="$WEBUI_ADMIN_USER"
WEBUI_ADMIN_PASSWORD="$WEBUI_ADMIN_PASSWORD"
EOF_LOCAL_ENV
}

# create and load local_environment
if [ ! -f "local_environment.sh" ]; then
  takenote "First-time setup"
  # need to gather input from user and generate some passwords
  read -srp "Enter a password for the WebUI admin account: " WEBUI_ADMIN_PASSWORD
  echo ""
  read -srp " Enter it again: " WEBUI_ADMIN_PASSWORD_AGAIN
  echo ""

  if [ "${WEBUI_ADMIN_PASSWORD}" != "${WEBUI_ADMIN_PASSWORD_AGAIN}" ]; then
    # dont use bail here because we dont want to set the failed flag
    echo "Error: passwords no not match!"
    exit 1
  fi

  if [ -z "$WEBUI_ADMIN_PASSWORD" ]; then
    # dont use bail here because we dont want to set the failed flag
    echo "Error: cannot have empty password!"
    exit 1
  fi

  # generate unique passwords for all our services
  DB_PASSWORD="$(generate_uuid)"
  BROKER_PASSWORD="$(generate_uuid)"
  SAMBA_PASSWORD="$(generate_uuid)"
  NFS_PASSWORD="$(generate_uuid)"

  # store everything for re-use later
  generate_local_env
fi

# shellcheck disable=SC1091
source local_environment.sh

######################################################  functions  ######################################################

function set_folder_perms () {
  local targetdir="$1"
  chown -R $SERVICE_USER:$SERVICE_GROUP "$targetdir" || bail "failed to chown dir: $targetdir"
  chmod 755 "$targetdir" || bail "failed to chmod dir: $targetdir"
}

function create_own_folder () {
  local targetdirs="$*"
  echo "creating dirs: $targetdirs"
  for targetdir in $targetdirs; do
    mkdir -p "$targetdir" || bail "failed to mkdir $targetdir"
    set_folder_perms "$targetdir"
  done
}

function check_packages () {
  # check if ALL of the given packages are installed
  local packages="$*"
  local all_installed="true"
  for thispkg in $packages; do
    dpkg -l |grep -q "$thispkg" || {
      all_installed="false"
    }
  done
  if [ "$all_installed" == "true" ]; then
    return 0
  else
    return 1
  fi
}

function install_packages () {
  local packages="$*"
  # shellcheck disable=SC2086
  check_packages $packages || {
    echo "Installing packages: $packages"
    apt-get update -q || bail "failed to update package repos"
    DEBIAN_FRONTEND=noninteractive apt-get install -y $packages || bail "failed to install packages"
    return 0
  }
  echo "Requested packages already installed: $packages"
  return 0
}

function copy_skel_file () {
  local skel_file="$1"
  if [ ! -f "/home/${SERVICE_USER}/${skel_file}" ]; then
    cp "/etc/skel/${skel_file}" "/home/${SERVICE_USER}/${skel_file}"
  fi
}

function create_service_user () {
  # ensure that the service user exists and belongs to service group
  id -g "$SERVICE_GROUP" >/dev/null 2>&1 || {
    groupadd "$SERVICE_GROUP" || bail "failed to create group: $SERVICE_GROUP"
  }
  id -u "$SERVICE_USER" >/dev/null 2>&1 || {
    useradd -g "$SERVICE_GROUP" "$SERVICE_USER" || bail "failed to create user: $SERVICE_USER"
  }
  create_own_folder /home/${SERVICE_USER}
  copy_skel_file ".profile"
  copy_skel_file ".bashrc"
  copy_skel_file ".bash_logout"
}

######################################################  Actual work starts here  ######################################################

announce "Taking over this server. Resistance is futile. You ($(hostname)) will be assimilated."

create_service_user
SERVICE_UID="$(id -u $SERVICE_USER)"
SERVICE_GID="$(id -g $SERVICE_GROUP)"
generate_local_env

# shellcheck disable=SC2086
install_packages $PKGS_PREREQS $PKGS_QEMU $PKGS_LDAP

takenote "disabling nfs-kernel-server from starting on boot, or it will get super confused"
systemctl disable nfs-kernel-server

takenote "disabling mosquitto.service"
systemctl stop mosquitto.service || bail "failed to stop mosquitto"
systemctl disable mosquitto.service || bail "failed to disable mosquitto"

takenote "installing: $PKGS_DOCKER"
install_docker_repo
# shellcheck disable=SC2086
install_packages $PKGS_DOCKER


# make folders
takenote "creating folder tree"
create_own_folder "${LOCAL_DIR}" "${NS_CONFIGDIR}" 
create_own_folder "${LOCAL_DIR}/database" "${LOCAL_DIR}/broker" "${LOCAL_DIR}/broker/config" "${LOCAL_DIR}/nfs"
create_own_folder "${NS_CONFIGDIR}/boot_images" "${NS_CONFIGDIR}/certs" "${NS_CONFIGDIR}/unattended_configs"
create_own_folder "${NS_CONFIGDIR}/stage1_files" "${NS_CONFIGDIR}/stage4" "${NS_CONFIGDIR}/uboot_scripts"
create_own_folder "${NS_CONFIGDIR}/ipxe_builds" "${NS_CONFIGDIR}/wimboot_builds" "${NS_CONFIGDIR}/uboot_binaries"
create_own_folder "${NS_CONFIGDIR}/packages" "${NS_CONFIGDIR}/tftp_root" "${NS_CONFIGDIR}/iso" "${NS_CONFIGDIR}/temp"


./bin/generate_config.sh || bail "failed go generate netbootstudio config file!"
./bin/generate_nfs_config.sh || bail "failed to generate nfs config file!"
./bin/generate_docker_compose.sh || bail "failed to generate docker compose file!"
./bin/generate_broker_config.sh || bail "failed to generate broker config file!"


# ensure ownership and permissions recursively
set_folder_perms "${LOCAL_DIR}"
set_folder_perms "${NS_CONFIGDIR}" 

takenote "Success! Marking first_time_setup_complete"
set_flag "first_time_setup_complete" || bail "failed to leave first_time_setup_complete flag!"

check_certs ${NS_CONFIGDIR}
echo ""
echo "  You also MUST reboot before trying to run Netboot Studio!"
echo ""
echo "  First-time setup complete. After reboot, you can deploy Netboot Studio with (as the non-root user):"
echo "    cd NetbootStudio-V2"
echo "    ./deploy.sh"
echo ""

