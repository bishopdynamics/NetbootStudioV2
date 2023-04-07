#!/usr/bin/env bash

# run a test ubuntu webinstaller build using the defaults inside the container

SCRIPT_FILENAME="NSTask_Image_UbuntuWeb.py"

./test-image.sh "python3 ${SCRIPT_FILENAME}"
