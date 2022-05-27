#!/usr/bin/env bash

# run the tftp server for testing (not in docker container)

if [ "$(id -u)" -gt 0 ]; then
  echo "need to run as root, trying sudo"
  sudo "${0}"
  exit
fi

VENV="venv"  # folder for virtualenv

if [ ! -f "${VENV}/bin/python" ]; then
  echo "missing venv"
  exit 1
fi



source ${VENV}/bin/activate
python3 NS_Service_TFTP.py -m dev -c /opt/NetbootStudio
deactivate
