#!/usr/bin/env bash

# run a test debian webinstaller build using the defaults inside the container

SCRIPT_FILENAME="NSTask_Image_DebianWeb.py"

./test-image.sh "python3 ${SCRIPT_FILENAME}"
