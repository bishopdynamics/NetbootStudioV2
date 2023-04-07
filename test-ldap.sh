#!/usr/bin/env bash
# test the ldap module

# VENV="venv"  # folder for virtualenv

# if [ ! -f "${VENV}/bin/python" ]; then
#   echo "missing venv"
#   exit 1
# fi

# source ${VENV}/bin/activate
# python3 NSLDAP.py -m dev -c /opt/NetbootStudio
# deactivate

SCRIPT_FILENAME="NSLDAP.py"

./test-image.sh "python3 ${SCRIPT_FILENAME}"
