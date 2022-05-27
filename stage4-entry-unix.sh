#!/usr/bin/env bash
# this is the stage4-entry script for unix-style systems

# the following vars will be provided by Netboot Studio
#export STAGE_SERVER="%s"  # ex: "http://192.168.1.123:8082"
#NEXT_SCRIPT="%s"  # ex: "profile-docker.sh" (or "none")

# must be root
if [ "$(id -u)" -gt 0 ]; then
    echo "need to run as root"
    exit 1
fi


echo "STAGE_SERVER: $STAGE_SERVER"
echo "NEXT_SCRIPT: $NEXT_SCRIPT"

# make a noticible break in the logs
# 	input: message
function announce () {
    local MESSAGE="$*"
    echo "#########################  $MESSAGE  #########################"
}

# make a louder, more obvious break in logs
# 	input: message
function announce_loud () {
    local MESSAGE="$*"
    echo "####################################################################################################"
    echo "#################################################  $MESSAGE  #########################"
    echo "####################################################################################################"
}

# an anternate view, we use this to distinguish apt-get stuff
# 	input: message
function announce_alt () {
    local MESSAGE="$*"
    echo "/////////////////////////  $MESSAGE  /////////////////////////"
}

# report given error and exit immediately; this is how we handle all errors
# 	input: message
function bail () {
    local MESSAGE="$*"
    echo "[stage4:bail] An error occured: $MESSAGE"
    signal_client_state_error "bail error" "$MESSAGE"
    exit 1
}

# fetch a given script then source it
# 	input: script_name
function source_stage4_script () {
    local SCRIPT_NAME="$1"
    local FULL_URL="${STAGE_SERVER}/stage4.sh?file=${SCRIPT_NAME}"
    announce_loud "sourcing a stage4 script: $SCRIPT_NAME"
    echo "[source_stage4_script] fetching $FULL_URL"
    wget -q -O "/post_install/${SCRIPT_NAME}" "${FULL_URL}" || bail "failed to download stage4 script named: $SCRIPT_NAME"
    # shellcheck disable=SC1090
    source "/post_install/${SCRIPT_NAME}"
    announce_loud "finished stage4 script: $SCRIPT_NAME"
}

# signal that this client has completed stage4
function signal_client_state_complete () {
    echo "doing: curl -G --data-urlencode \"state=complete\" \"${STAGE_SERVER}/client_state\""
    curl -G --data-urlencode "state=complete" "${STAGE_SERVER}/client_state"
}

# signal that the client has an an error with description
function signal_client_state_error () {
  local ERROR_SHORT="$1"
  local ERROR_DESCRIPTION="$2"
  echo "doing: curl -G --data-urlencode \"error_short=${ERROR_SHORT}\" --data-urlencode \"description=${ERROR_DESCRIPTION}\" \"${STAGE_SERVER}/client_state\" "
  curl -G --data-urlencode "state=error" --data-urlencode "error_short=${ERROR_SHORT}" --data-urlencode "description=${ERROR_DESCRIPTION}" "${STAGE_SERVER}/client_state"
}

# a package is just a tar.gz with package-meta/install.sh inside it
# 	input: package_name
function install_package () {
    local PACKAGE_NAME="$1"
    local PACKAGE_FILE="/post_install/packages/${PACKAGE_NAME}.tar.gz"
    local PACKAGE_URL="${STAGE_SERVER}/packages/${PACKAGE_NAME}.tar.gz"
    local TEMP_DIR; TEMP_DIR=$(mktemp -d)
    mkdir -p "$TEMP_DIR"
    announce_loud "installing a stage4 package: $PACKAGE_NAME"
    mkdir -p /post_install/packages
    echo "[install_package] fetching $PACKAGE_URL"
    wget -q -O "$PACKAGE_FILE" "$PACKAGE_URL" || bail "failed to download stage4 package named: $PACKAGE_NAME"
    tar xf "$PACKAGE_FILE" -C "${TEMP_DIR}/" || bail "failed to extract stage4 package named: $PACKAGE_NAME"
    bash "${TEMP_DIR}/package-meta/install.sh" "${TEMP_DIR}" || bail "failed while running install.sh for package: $PACKAGE_NAME"
    rm -r "$TEMP_DIR"
    announce_loud "finished installing stage4 package: $PACKAGE_NAME"
}

# add a line to a file, unless that exact line is already present
# 	input: line, file
function add_line_to_file () {
    local LINE="$1"
    local FILE="$2"
    grep -qFx "${LINE}" "$FILE" || {
        echo "$LINE" >> "$FILE" || {
            bail "error while appending line to file: $FILE"
        }
    }
}

# perform an apt-get command, but we make it show progress all nice-like
# 	input: apt_command_string
function do_apt () {
    echo "apt-get $*"
    # shellcheck disable=SC2086,SC2048  # ignore the un-quoted $*
#    debconf-apt-progress -- apt-get $* || {
#        bail "something failed while doing apt-get $*"
#    }
    # TODO put back debconf-apt-progress
    apt-get $* || {
          bail "something failed while doing apt-get $*"
      }
}

# install something from apt
#	input: packages
function apt_install () {
    # shellcheck disable=SC2086,SC2048  # ignore the un-quoted $*
    do_apt install -y $*
}

# given a url to a key, install it for apt
# 	input: key_url
function add_apt_key () {
    # TODO this is actually deprecated, we need to do it the right way
    #	https://askubuntu.com/questions/1286545/what-commands-exactly-should-replace-the-deprecated-apt-key
    local REPO_KEY_URL="$1"
    echo "adding repo key: $REPO_KEY_URL"
    curl -fsSL "$REPO_KEY_URL" | apt-key add -qq - || {
            bail "failed to install key from: $REPO_KEY_URL"
        }
}

# add a given apt repo by url and name
# 	input: repo_line, repo_name, repo_key_url
# NOTE: do not include "deb" in repo_line
# example: add_apt_repo "http://apt.armbian.com bullseye main bullseye-utils bullseye-desktop" "armbian" "http://apt.armbian.com/armbian.key"
function add_apt_repo () {
    local REPO_LINE="$1"
    local REPO_NAME="$2"
    local REPO_KEY_URL="$3"
    add_apt_key "$REPO_KEY_URL"
    echo "adding repo: $REPO_LINE"
    if [ ! -d /etc/apt/sources.list.d ]; then
        mkdir -p /etc/apt/sources.list.d
    fi
    echo "# added by stage4:add_apt_repo for $REPO_NAME" > "/etc/apt/sources.list.d/${REPO_NAME}.list" || {
        bail "failed to add repo named: $REPO_NAME"
    }
    echo "deb $REPO_LINE" >> "/etc/apt/sources.list.d/${REPO_NAME}.list" || {
        bail "failed to add repo named: $REPO_NAME"
    }
    do_apt update || {
        bail "failed to update apt after adding repository"
    }
}

# now lets do some work
if [ "$NEXT_SCRIPT" == "none" ]; then
  announce "skipping stage4. script: none"
else
  source_stage4_script "$NEXT_SCRIPT"
fi

signal_client_state_complete
announce_loud "end of stage4-entry-unix.sh"
