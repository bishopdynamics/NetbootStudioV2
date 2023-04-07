#!/usr/bin/env bash
python NSTask_BuildiPXE.py

# run a test ipxe build using the defaults inside the container

SCRIPT_FILENAME="NSTask_BuildiPXE.py"

./test-image.sh "python3 ${SCRIPT_FILENAME}"
