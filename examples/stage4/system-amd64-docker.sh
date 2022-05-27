#!/usr/bin/env bash
# depends on stage4 functions

# sets up an amd64 machine for docker

######################## Config

NFS_SHARE_DOCKER="192.168.1.198:/mnt/MassStorage/Local/Docker"  # nfs share that will be mounted at /mnt/docker-nfs
NFS_SHARE_DOCKER_MOUNTPOINT="/mnt/docker-nfs"
NFS_SHARE_OPTS="v3,rw,retry=4,_netdev,x-systemd.automount"

######################## Work functions


# mount the docker nfs share
function setup_nfs_share () {
    announce "setting up nfs share for docker: $NFS_SHARE_DOCKER_MOUNTPOINT"
    mkdir -p "$NFS_SHARE_DOCKER_MOUNTPOINT" || {
        bail "failed to create $NFS_SHARE_DOCKER_MOUNTPOINT"
    }
    add_line_to_file "# nfs share $NFS_SHARE_DOCKER_MOUNTPOINT" /etc/fstab
    add_line_to_file "$NFS_SHARE_DOCKER ${NFS_SHARE_DOCKER_MOUNTPOINT} nfs ${NFS_SHARE_OPTS} 0 0" /etc/fstab
    apt_install cifs-utils nfs-common
}


# sync to our local ntp server
function setup_ntp_server () {
    announce "setting up ntp client"
    # not using add_line_to_file because we want to completely overwrite the existing file
    echo "server 192.168.1.1 prefer iburst" > /etc/ntp.conf
    # timedatectl set-timezone "America/Los_Angeles"
    # timedatectl set-ntp true
}


########################## Do the work
source_stage4_script "app-monitoringagent.sh"
source_stage4_script "user-james.sh"
source_stage4_script "app-docker.sh"
setup_ntp_server
setup_nfs_share

