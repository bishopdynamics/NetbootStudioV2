#!/usr/bin/env bash

# run a test debian liveimage build using the defaults inside the container

SCRIPT_FILENAME="NSTask_Image_DebianLive.py"

./test-image.sh "python3 ${SCRIPT_FILENAME}"
