FROM debian:bullseye-slim

# needed: python3-pip build-essential git sed grep mtools perl genisoimage liblzma-dev syslinux binutils unzip isolinux
# for arm cross compile (wip): gcc-aarch64-linux-gnu g++-aarch64-linux-gnu device-tree-compiler

ARG SERVICE_USER
ARG SERVICE_GROUP
ARG SERVICE_UID
ARG SERVICE_GID

WORKDIR /opt/NetbootStudio_bin

# set timezone and refresh apt cache
RUN apt-get update
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y tzdata
RUN DEBIAN_FRONTEND="noninteractive" apt-get update

# common utilities
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y build-essential python3 python3-pip perl sed grep gawk git iproute2 wget curl zip p7zip-full unzip

# tools needed for building boot images
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y coreutils binutils mtools isolinux genisoimage syslinux live-build live-config-doc live-boot-doc u-boot-tools liblzma-dev libpcap0.8 

# packages for cross-compiling
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y gcc-aarch64-linux-gnu iasl lzma-dev subversion uuid-dev binutils-dev libiberty-dev pesign gcab g++-aarch64-linux-gnu device-tree-compiler

# qemu packages so we can build live-images for other arch
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y qemu qemu-system qemu-user-static


# prereqs for building python-ldap wheel
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y python3-dev libldap2-dev libsasl2-dev ldap-utils tox lcov valgrind

# install python modules from requirements.txt
COPY requirements.txt ./
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install --upgrade setuptools wheel
RUN python3 -m pip install -r requirements.txt
COPY . .


# grab our full version string
COPY tmp/VERSION ./

# trust our ca certificate
COPY tmp/ca_cert.pem /usr/local/share/ca-certificates/NetbootStudio_ca.pem
RUN chmod 644 /usr/local/share/ca-certificates/NetbootStudio_ca.pem
RUN update-ca-certificates

# make this all run as a non-root user
RUN groupadd -g ${SERVICE_GID} ${SERVICE_GROUP}
RUN useradd ${SERVICE_USER} -u ${SERVICE_UID} -g ${SERVICE_GID} -m -s /bin/bash
RUN chown -R ${SERVICE_USER}:${SERVICE_GROUP} /opt/NetbootStudio_bin

USER root
EXPOSE 8080
EXPOSE 8081
EXPOSE 8082
EXPOSE 8083
EXPOSE 9069
