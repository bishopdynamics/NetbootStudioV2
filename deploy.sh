#!/usr/bin/env bash
# Build and deploy all Netboot Studio containers and config

# Flags:
#   -f    Flush all docker image caches before building images.
#           forces all layers to be rebuilt. Will take much longer to build images

source ./bin/nscommon.bashlib || {
  echo "failed to source nscommon.bashlib"
  exit 1
}

# must be run as root
check_root

function bail() {
  echo "Error: $*"
  exit 1
}

FRESH_BUILD="False"
if [ "$1" == "-f" ]; then
  FRESH_BUILD="True"
fi

announce "Deploying Netboot Studio"

takenote "lets check some flags"
check_flag_set "first_time_setup_failed" && bail "first_time_setup_failed flag exists, you need to start over with a fresh Debian 11 installation. Contact Support."
check_flag_set "first_time_setup_complete" || bail "need to run: ./setup.sh (and reboot) first"
if [ ! -f "local_environment.sh" ]; then
  echo "missing local_environment.sh, but first_time_setup_complete flag exists, so something is wrong. Contact Support."
  exit 1
fi

# shellcheck disable=SC1091
source "local_environment.sh"

function set_folder_perms () {
  local targetdir="$1"
  chown -R "$SERVICE_USER":"$SERVICE_GROUP" "$targetdir" || bail "failed to chown dir: $targetdir"
  chmod 755 "$targetdir" || bail "failed to chmod dir: $targetdir"
}



##### Start work here

check_certs "${NS_CONFIGDIR}" || exit 1

echo "checking config file"
if [ ! -f "${NS_CONFIGDIR}/config.ini" ]; then
  bail "Did not find config.ini, setup.sh failed. Contact Support."
fi



takenote "Stopping any running containers"
./stop.sh || bail "failed to stop existing containers"

takenote "Stopping NFS Server"
systemctl stop nfs-kernel-server || bail "failed to stop nfs server"

if [ "$FRESH_BUILD" == "True" ]; then
  ./build-image.sh -f
else
  ./build-image.sh
fi

takenote "Re-generating config files"
./bin/generate_config.sh || bail "failed go generate netbootstudio config file!"
./bin/generate_nfs_config.sh || bail "failed to generate nfs config file!"
./bin/generate_docker_compose.sh || bail "failed to generate docker compose file!"
./bin/generate_broker_config.sh || bail "failed to generate broker config file!"

# ensure ownership and permissions recursively
set_folder_perms "${LOCAL_DIR}"
set_folder_perms "${NS_CONFIGDIR}" 

takenote "Starting containers"
docker-compose up -d || bail "failed to bring up containers"

takenote "Starting NFS Server"
systemctl start nfs-kernel-server || bail "failed to start nfs-kernel-server!"

echo ""
echo " Success! You can access the WebUI at: https://$(hostname)/"
echo "   services may take up to 30 seconds to be available"
echo "   to monitor logs, run: ./monitor.sh"
echo ""

exit 0
