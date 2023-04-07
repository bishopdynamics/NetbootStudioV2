#!/usr/bin/env bash

# run the webui service for testing (not in docker container)

VENV="venv"  # folder for virtualenv

if [ ! -f "${VENV}/bin/python" ]; then
  echo "missing venv"
  exit 1
fi

source ${VENV}/bin/activate
python3 NS_Service_WebUI.py -m dev -c /opt/NetbootStudio
deactivate
