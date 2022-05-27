#!/usr/bin/env bash
# depends on stage4 functions

# this installs docker 

if [ "$DOCKER_USE_DISTRO_VERSION" == "True" ]; then
	announce "installing docker from distro provided package"
else
	announce "adding docker apt repository"
	# remember not to include "deb" at beginning of this line
	add_apt_repo "[arch=$(dpkg --print-architecture)] https://download.docker.com/linux/debian $(lsb_release -cs) stable" "docker" "https://download.docker.com/linux/debian/gpg"
fi

announce "installing docker and docker-compose"
apt_install --no-install-recommends docker-ce docker-ce-cli containerd.io docker-compose
usermod -a -G docker james || {
    bail "failed to add user: james to the group: docker"
}