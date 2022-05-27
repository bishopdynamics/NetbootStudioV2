#!/usr/bin/env bash

# run a test ipxe build using the defaults

VENV="venv"  # folder for virtualenv

if [ ! -f "${VENV}/bin/python" ]; then
  echo "missing virtualenv"
  exit 1
fi

source ${VENV}/bin/activate
python NSTask_BuildiPXE.py

deactivate
