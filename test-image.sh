#!/usr/bin/env bash

# test the container image we built

CONTAINER_NAME="netbootstudio_test"

./build-image.sh

if [ -z "$1" ]; then
  echo "Testing netbootstudio image as a container named $CONTAINER_NAME"
  docker run -it --privileged --name=${CONTAINER_NAME} \
    --mount type=bind,source=/etc/timezone,target=/etc/timezone,readonly \
    --mount type=bind,source=/opt/NetbootStudio,target=/opt/NetbootStudio \
    bishopdynamics/netbootstudio:latest /bin/bash && echo "exited cleanly"
else
  echo "Testing netbootstudio image as a container named $CONTAINER_NAME with command: $*"
  docker run -it --privileged --name=${CONTAINER_NAME} \
    --mount type=bind,source=/etc/timezone,target=/etc/timezone,readonly \
    --mount type=bind,source=/opt/NetbootStudio,target=/opt/NetbootStudio \
    bishopdynamics/netbootstudio:latest /bin/bash -c "$*;" && echo "exited cleanly"
fi

echo "Cleaning up just in case something went wrong above. Errors below here are OK"
docker stop "${CONTAINER_NAME}"
docker rm "${CONTAINER_NAME}"
echo "done"
