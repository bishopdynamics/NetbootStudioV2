FROM ubuntu:20.04

# needed: python3-pip build-essential git sed grep mtools perl genisoimage liblzma-dev syslinux binutils unzip isolinux
# for arm cross compile (wip): gcc-aarch64-linux-gnu g++-aarch64-linux-gnu device-tree-compiler

WORKDIR /opt/NetbootStudio_bin
# base packages needed for all the things
RUN apt-get update
ENV TZ=America/Los_Angeles
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y tzdata
RUN DEBIAN_FRONTEND="noninteractive" apt-get update
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y python3 python3-pip build-essential iproute2 wget curl zip git sed grep mtools perl genisoimage liblzma-dev binutils unzip isolinux perl gawk coreutils u-boot-tools libpcap0.8
# packages for cross-compiling
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y gcc-aarch64-linux-gnu iasl lzma-dev subversion uuid-dev binutils-dev libiberty-dev pesign gcab g++-aarch64-linux-gnu device-tree-compiler
# qemu packages so we can build live-images for other arch
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y qemu qemu-system
COPY requirements.txt ./
RUN python3.8 -m pip install -r requirements.txt
COPY . .
# grab our full version string
COPY tmp/VERSION ./
# make this all run as a non-root user
RUN useradd netboot && chown -R netboot /opt/NetbootStudio_bin
USER root
EXPOSE 8080
EXPOSE 8081
EXPOSE 8082
EXPOSE 8083
EXPOSE 9069
