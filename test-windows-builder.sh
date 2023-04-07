#!/usr/bin/env bash

# run a test windows from iso build using the defaults inside the container

SCRIPT_FILENAME="NSTask_Image_WindowsFromISO.py"

./test-image.sh "python3 ${SCRIPT_FILENAME}"
