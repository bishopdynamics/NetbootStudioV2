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

announce "Building docker image for netbootstudio"

if [ ! -f "local_environment.sh" ]; then
  echo "missing local_environment.sh, but first_time_setup_complete flag exists, so something is wrong. Contact Support."
  exit 1
fi

# shellcheck disable=SC1091
source "local_environment.sh"

##### Start work here

if [ "$FRESH_BUILD" == "True" ]; then
  takenote "Flushing all docker image caches before build"
  docker system prune -a -f
fi

takenote "Rebuilding docker image"
# rebuild the image from source
takenote "Rebuilding image..."
mkdir -p ./tmp || bail "failed to create folder: ./tmp"
# shellcheck disable=SC2002
echo "$(cat "VERSION" | tr -d '\n' |tr -d '\r')-$(git rev-parse --short HEAD)-$(uname)-$(uname -m)" > ./tmp/VERSION

cp "${NS_CONFIGDIR}/certs/ca_cert.pem" tmp/ca_cert.pem
docker build --build-arg SERVICE_USER="$SERVICE_USER" --build-arg SERVICE_GROUP="$SERVICE_GROUP" --build-arg SERVICE_UID="$SERVICE_UID" --build-arg SERVICE_GID="$SERVICE_GID" -t bishopdynamics/netbootstudio  . || bail "failed to build docker image"
rm -r ./tmp || bail "failed to clean up folder: ./tmp"


takenote "building custom code-server image..."
docker build --build-arg SERVICE_USER="$SERVICE_USER" --build-arg SERVICE_GROUP="$SERVICE_GROUP" --build-arg SERVICE_UID="$SERVICE_UID" --build-arg SERVICE_GID="$SERVICE_GID" --pull -t bishopdynamics/code-server:latest ./code-server || bail "failed to build code-server image"


takenote "finished building image"

exit 0
