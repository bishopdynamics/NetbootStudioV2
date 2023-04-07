#!/usr/bin/env bash
# Netboot Studo reset script

echo ""
echo "Reset Netboot Studio database and config, but NOT your data"
echo ""
echo "Will delete: /opt/local, /opt/NetbootStudio/config.ini, /opt/NetbootStudio/settings.json, local_environment.sh, docker-compose.yml"
echo "Are you sure you want to reset this system? enter Y to continue "
read -r ANSWER

function remove_file () {
    local filepath="$1"
    echo "Removing file: $filepath"
    rm "$filepath"
}

function remove_folder () {
    local filepath="$1"
    echo "Removing folder: $filepath"
    rm -r "$filepath"
}

if [ "$ANSWER" == "Y" ]; then
    echo "Resetting this system"
    ./stop.sh
    remove_folder /opt/local
    remove_file /opt/NetbootStudio/config.ini
    remove_file /opt/NetbootStudio/settings.json
    remove_file local_environment.sh
    remove_file docker-compose.yml
    echo "removing flags"
    rm /opt/flag-netbootstudio-*
    echo "Reset complete"
else
    echo "Reset aborted"
    exit 1
fi