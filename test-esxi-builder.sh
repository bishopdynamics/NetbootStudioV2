#!/usr/bin/env bash

# run a test esx from iso build using the defaults inside the container

SCRIPT_FILENAME="NSTask_Image_ESXFromISO.py"

./test-image.sh "python3 ${SCRIPT_FILENAME}"
