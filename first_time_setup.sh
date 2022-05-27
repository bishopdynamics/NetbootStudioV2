#!/usr/bin/env bash
# Netboot Studo first-time setup wizard

source nscommon.bashlib || {
  echo "failed to source nscommon.bashlib"
  exit 1
}
# must be run as root
check_root
function bail () {
  set_flag first_time_setup_failed
  echo "First-Time Setup Failed!"
	echo " Error: $*"
	exit 1
}

check_flag_set "first_time_setup_complete" && bail "first_time_setup_complete flag exists, already ran first_time_setup.sh!"
#check_flag_set "first_time_setup_failed" && bail "first_time_setup_failed flag exists, you need to start over with a fresh Debian 11 installation. Contact Support."

# TODO why root doesnt have /usr/sbin in path?
PATH=/usr/sbin:$PATH

# we dont care what you want, we are using these options, deal with it
#HARDCODED_NFS_OPTS="v3,rw,retry=4,_netdev,x-systemd.automount"
# this is hardcoded in several other places as well
HARDCODED_NS_CONFIGDIR="/opt/NetbootStudio"
THIS_HOSTNAME=$(hostname)
THIS_IP=$(get_ip_address)


announce "Netboot Studio First-Time Setup Wizard"

takenote "Lets set this thing up"

read -rp "What local (non-root) user will this run as?: " GIVEN_NON_ROOT_USERNAME
read -rp "What is that user's primary group?: " GIVEN_NON_ROOT_GROUPNAME

#echo "  Example of NFS path: 192.168.1.198:/mnt/MassStorage/Local/NetbootStudioV2"
#read -rp "What is the path to the NFS share that we will mount at /opt/NetbootStudio ?: " GIVEN_NFS_SHARE
read -srp "Enter a password for the WebUI admin account: " API_PASSWORD
echo ""
read -srp " Enter it again: " API_PASSWORD_AGAIN
echo ""

if [ "${API_PASSWORD}" != "${API_PASSWORD_AGAIN}" ]; then
  # dont use bail here because we dont want to set the failed flag
  echo "Error: passwords no not match!"
  exit 1
fi

# TODO actually validate this input
if [ -z "$GIVEN_NON_ROOT_USERNAME" ] || [ -z "$GIVEN_NON_ROOT_GROUPNAME" ] || [ -z "$API_PASSWORD" ]; then
  # dont use bail here because we dont want to set the failed flag
  echo "Error: one of your responses was empty!"
  exit 1
fi

echo ""
echo "Will now configure this server for Netboot Studio"
echo "  Netboot Studio will make this server its own, are you sure you wish to continue?"
read -rp "  hit enter to continue, ctrl+c to abort" NOTHING
echo "$NOTHING" >/dev/null

announce "Taking over this server. Resistance is futile. You ($(hostname)) will be assimilated."

takenote "alright, alright, alright. Let's do this."

# make folders
takenote "making and chowning folders"
mkdir -p /opt/local/database || bail "failed to make a folder we need"
mkdir -p /opt/local/broker/config || bail "failed to make a folder we need"
mkdir -p "${HARDCODED_NS_CONFIGDIR}" || bail "failed to make a folder we need"
chown -R "$GIVEN_NON_ROOT_USERNAME":"$GIVEN_NON_ROOT_GROUPNAME" /opt/local || bail "failed to chown a folder as ${GIVEN_NON_ROOT_USERNAME}:${GIVEN_NON_ROOT_GROUPNAME}"
chown -R "$GIVEN_NON_ROOT_USERNAME":"$GIVEN_NON_ROOT_GROUPNAME" "${HARDCODED_NS_CONFIGDIR}" || bail "failed to chown a folder as ${GIVEN_NON_ROOT_USERNAME}:${GIVEN_NON_ROOT_GROUPNAME}"

# need to install nfs stuff first so that we can mount it early as possible (and fail early)
announce "installing nfs-common early so we can test mounting the share. If it fails, there is something wrong with the NFS share you provided"
apt-get update || bail "failed to update apt"
takenote "update done"
#apt-get dist-upgrade -y || bail "failed to dist-upgrade"
#takenote "dist-upgrade done"
apt-get install -y nfs-common || bail "failed to install package: nfs-kernel-server"
takenote "nfs-kernel-server install done"

#announce "Lets try mounting that NFS share you gave us, just in case it gives us any attitude"
#takenote "trying to unmount ${HARDCODED_NS_CONFIGDIR} just in case"
#umount "${HARDCODED_NS_CONFIGDIR}" || {
#  takenote "   Whatever, you're not the boss of me"
#}
#takenote "adding entry for nfs share to /etc/fstab on host"
#cat << EOF_FSTAB >> /etc/fstab
#
## Netboot Studio
#${GIVEN_NFS_SHARE} ${HARDCODED_NS_CONFIGDIR} nfs ${HARDCODED_NFS_OPTS} 0 0
#
#EOF_FSTAB
#
## TODO cant use || to bail on failing to write this, so we need to check for it after the fact or something
#takenote "that was nice. I hope that worked. You are checking my work, right? Right?"
#takenote "lets just try to mount it."
#mount "${HARDCODED_NS_CONFIGDIR}" || {
#  takenote "huh, thats not good"
#  bail "failed to mount ${GIVEN_NFS_SHARE} at ${HARDCODED_NS_CONFIGDIR}"
#}
#takenote "if I'm reading this right, and I'd like to think that I am, that didn't not work! thats good right?"


takenote "lets do it again with local_environment.sh !"
cat << EOF_LOCAL_ENV > local_environment.sh
GIVEN_NON_ROOT_USERNAME="$GIVEN_NON_ROOT_USERNAME"
GIVEN_NON_ROOT_GROUPNAME="$GIVEN_NON_ROOT_GROUPNAME"
GIVEN_NFS_SHARE="$GIVEN_NFS_SHARE"
EOF_LOCAL_ENV
takenote "neat, i'm having fun. Are you having fun?"
# TODO create local netbootstudio user on host, for NFS user
# TODO create netbootstudio user in samba container, with this generated password
# TODO make nfs and samba secure (no guest, only user netbootstudio)
takenote "no you're right, we should just keep this professional. Moving on."

API_USER="admin"
SERVICE_USER="netbootstudio"
DB_USER="${SERVICE_USER}"
BROKER_USER="${SERVICE_USER}"
SAMBA_USER="${SERVICE_USER}"
NFS_USER="${SERVICE_USER}"
takenote "ooh, I can see the users for your services from here! Oh, they're all ${SERVICE_USER}. How creative."

takenote "ok, lets do something actually fun: generate some passwords!"
DB_PASSWORD=$(generate_uuid)
BROKER_PASSWORD=$(generate_uuid)
SAMBA_PASSWORD=$(generate_uuid)
NFS_PASSWORD=$(generate_uuid)

takenote "I sure hope all the things we're setting up here are ok with a full uuid.uuid4() strings as passwords, cuz thats what's happening here"

takenote "alright enough of that, lets let apt out for a walk. Here boy!"
apt-get update

takenote "thats a good apt. Now go install sudo"
apt-get install sudo || bail "failed to install sudo"
takenote "good boy ! thats a good apt !"
takenote "and because I'm a generous and trusting god, I will grant you nopasswd sudo via /etc/sudoers.d/${GIVEN_NON_ROOT_USERNAME}-nopasswd"
mkdir -p /etc/sudoers.d || bail "huh, we failed while trying to create /etc/sudoers.d, thats weird..."
echo "${GIVEN_NON_ROOT_USERNAME} ALL=(ALL) NOPASSWD: ALL" > "/etc/sudoers.d/${GIVEN_NON_ROOT_USERNAME}-nopasswd" || bail "failed to create /etc/sudoers.d/${GIVEN_NON_ROOT_USERNAME}-nopasswd"

takenote "ok, lets take a look at the side of the box. it says here the base prereqs are: mosquitto-clients mosquitto nfs-kernel-server htop iftop iotop gnupg2 git curl whois"
apt-get install -y mosquitto-clients mosquitto nfs-kernel-server htop iftop iotop gnupg2 git curl whois || bail "failed to install base prereqs"

takenote "now lets prevent nfs-kernel-server from starting on boot, or it will get super confused"
systemctl disable nfs-kernel-server

takenote "that wasn't so bad."
takenote "wait..."
takenote "what's that buzzing noise?"
takenote "  can you hear that?"

takenote "Oh right! we installed mosquitto. we only need mosquitto_passwd on the host side of things. Lets squash that thing"
systemctl stop mosquitto.service || bail "failed to stop mosquitto"
systemctl disable mosquitto.service || bail "failed to disable mosquitto"
takenote "aahhhh, that's better."

#takenote "ok, I think apt is ready to be introduced to new repos. Here, lets try out https://download.docker.com/linux/debian"
#takenote "i'm gonna need a key for that"
#curl -fsSl https://download.docker.com/linux/debian/gpg |apt-key add -qq - || bail "failed to add apt key for docker repo"
#takenote "ughhhh, I know. i'll get to it, i'll get to it. do it anyway."
#echo "deb [arch=$(dpkg --print-architecture)] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list || bail "failed to create docker repo list file"
#apt-get update || bail "failed to update after adding repo"
#
#takenote "alright, lets take that repo for a run and install: docker-ce docker-ce-cli containerd.io docker-compose"
#apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose || bail "failed to install docker"

takenote "and since you're being so good, i'll let you join the docker group. its the cool people group."
usermod -a -G docker "$GIVEN_NON_ROOT_USERNAME" || bail "failed to add user $GIVEN_NON_ROOT_USERNAME to group docker"

takenote "lets initialize that docker swarm, just because we can you know? I  was getting kinda bored with all that apt stuff."
# TODO do we even need swarm anymore? we need it for portainer, which is handy, but i dont think netboot studio itself needs it
docker swarm init || echo "failed to docker swarm init, but i'm strangely comfortable with it"

takenote "neat. "

takenote "while we're here, I'm feeling extra generous. Lets install all the packages needed for developing task scripts on the host side of things"
takenote "installing additional prereqs for development: qemu-utils qemu-efi-aarch64 qemu-system-arm qemu-user-static gcc make sed grep perl genisoimage liblzma-dev binutils unzip isolinux mtools u-boot-tools live-build"
apt-get install -y qemu-utils qemu-efi-aarch64 python3-pip qemu-system-arm qemu-user-static gcc make sed grep perl genisoimage liblzma-dev binutils unzip isolinux mtools u-boot-tools live-build || bail "failed to install additional prereqs for development"


takenote "alright lets move on. ima double-check that the permissions on $HARDCODED_NS_CONFIGDIR are what we want"
if [ ! -d "$HARDCODED_NS_CONFIGDIR" ]; then
  echo "creating $HARDCODED_NS_CONFIGDIR"
  mkdir -p "${HARDCODED_NS_CONFIGDIR}" || bail "failed to create ${HARDCODED_NS_CONFIGDIR}"
  chown "${GIVEN_NON_ROOT_USERNAME}:${GIVEN_NON_ROOT_GROUPNAME}" "${HARDCODED_NS_CONFIGDIR}" || bail "failed to chown ${HARDCODED_NS_CONFIGDIR} as ${GIVEN_NON_ROOT_USERNAME}:${GIVEN_NON_ROOT_GROUPNAME}"
fi

takenote "and how about /opt/local ? how's that looking?"
if [ ! -d "/opt/local" ]; then
  echo "creating /opt/local"
  mkdir -p /opt/local || bail "failed to create /opt/local"
  chown "${GIVEN_NON_ROOT_USERNAME}:${GIVEN_NON_ROOT_GROUPNAME}" /opt/local || bail "failed to chown /opt/local as ${GIVEN_NON_ROOT_USERNAME}:${GIVEN_NON_ROOT_GROUPNAME}"
fi

takenote "all gravy"

announce "ladies and gentlemen. the dining room proudly presents: a bunch of big-ass heredoc'd config files"

takenote "writing runtime config.ini"
# render runtime config.ini
cat << EOF_CONFIG_INI > "${HARDCODED_NS_CONFIGDIR}/config.ini"
; auto-generated by Netboot Studio first_time_setup.sh
[main]
; this is the ip of your netboot server, where all the services will run
netboot_server_ip = ${THIS_IP}
; the hostname of your netboot server
netboot_server_hostname = ${THIS_HOSTNAME}
; this is hardcoded in other places, dont touch
tftp_file = /ipxe.efi

[webserver]
port = 443
; this is only used to redirect to https
port_http = 80

[websocket]
port = 8081

[stageserver]
port = 8082

[tftp]
port = 69

[uploadserver]
port = 8084

[apiserver]
port = 8083
; credentials for accessing the webui
admin_user = ${API_USER}
admin_password = ${API_PASSWORD}

[database]
; these details must match in docker-compose.yml
port = 3306
database = netbootstudio
user = ${DB_USER}
password = ${DB_PASSWORD}

[broker]
; these details must match in docker-compose.yml
port = 8883
port_websocket = 8884
user = ${BROKER_USER}
password = ${BROKER_PASSWORD}

[samba]
user = ${SAMBA_USER}
password = ${SAMBA_PASSWORD}

[nfs]
user = ${NFS_USER}
password = ${NFS_PASSWORD}

EOF_CONFIG_INI


# https://mosquitto.org/man/mosquitto-conf-5.html
takenote "writing broker config"
cat << 'EOF_BROKER' > /opt/local/broker/config/mosquitto.conf
# auto-generated by Netboot Studio first_time_setup.sh
per_listener_settings true
allow_anonymous true

# not exposed, for testing (no ssl, no password)
listener 1883
socket_domain ipv4
allow_anonymous true

# for mqtts://
listener 8883
socket_domain ipv4
allow_anonymous false
password_file /mosquitto/config/password
#cafile /opt/NetbootStudio/certs/ca_cert.pem
capath /etc/ssl/certs/
keyfile /opt/NetbootStudio/certs/server_key.key
certfile /opt/NetbootStudio/certs/server_cert.pem

# for wss://
listener 8884
socket_domain ipv4
protocol websockets
allow_anonymous false
password_file /mosquitto/config/password
#cafile /opt/NetbootStudio/certs/ca_cert.pem
keyfile /opt/NetbootStudio/certs/server_key.key
certfile /opt/NetbootStudio/certs/server_cert.pem

EOF_BROKER

takenote "oh, this one is a little more involved. lets generate the broker password file"
command -v mosquitto_passwd || bail "missing mosquitto_passwd, you need to install the mosquitto package"
PW_FILE_TMP="/opt/local/broker/config/password.tmp"
PW_FILE="/opt/local/broker/config/password"
touch "$PW_FILE_TMP" || bail "cannot write /opt/local/broker/config/password"
echo "foo:bar" > "$PW_FILE_TMP"
mosquitto_passwd -b "$PW_FILE_TMP" "${BROKER_USER}" "${BROKER_PASSWORD}" || bail "failed to create mosquitto password file, maybe missing mosquitto_passwd?"
tail -n1 "$PW_FILE_TMP" > "$PW_FILE"
rm "$PW_FILE_TMP"

takenote "whew, i think i pulled something. i really need to start stretching before these things"
takenote "ah, another heredoc"

takenote "writing nfs exports config"
cat << 'EOF_NFS' > /etc/exports
# auto-generated by NetbootStudio first_time_setup.sh
/opt/NetbootStudio/boot_images *(ro,fsid=1,sync,no_wdelay,insecure_locks,insecure,no_subtree_check,all_squash,anonuid=1000,anongid=1000)

EOF_NFS


#takenote "how about we refresh the exports so that the nfs server starts working..."
#exportfs -r || bail "failed to restart nfs server"
#takenote "...now! *dance* "

takenote "Look, I dont want to, like, tell you how to do your job but... can you... ugh."
takenote "I'm just gonna write that docker-compose.yml for you"

cat << EOF_DOCKER_COMPOSE > docker-compose.yml
---
version: '3.6'

# auto-generated by first_time_setup.sh

# full stack of services
# this needs to run on host network with kernel capability NET_ADMIN, so it will not currently run in Docker Swarm.

services:
  NS-API:
    image: bishopdynamics/netbootstudio:latest
    restart: unless-stopped
    ports:
      - "8083:8083"
      - "8081:8081"
    volumes:
      - ${HARDCODED_NS_CONFIGDIR}:/opt/NetbootStudio
      - /etc/timezone:/etc/timezone:ro
    command: >
      /bin/bash -c "echo 'Delaying startup to wait for broker and database';sleep 10;python3 NS_Service_API.py -m prod -c /opt/NetbootStudio;"

  NS-FileWatcher:
    image: bishopdynamics/netbootstudio:latest
    restart: unless-stopped
    volumes:
      - ${HARDCODED_NS_CONFIGDIR}:/opt/NetbootStudio:ro
      - /etc/timezone:/etc/timezone:ro
    command: >
      /bin/bash -c "echo 'Delaying startup to wait for broker and database';sleep 10;python3 NS_Service_FileWatcher.py -m prod -c /opt/NetbootStudio;"

  NS-Uploader:
    image: bishopdynamics/netbootstudio:latest
    restart: unless-stopped
    ports:
      - "8084:8084"
    volumes:
      - ${HARDCODED_NS_CONFIGDIR}:/opt/NetbootStudio
      - /etc/timezone:/etc/timezone:ro
    command: >
      /bin/bash -c "echo 'Delaying startup to wait for broker and database';sleep 10;python3 NS_Service_Uploader.py -m prod -c /opt/NetbootStudio;"

  NS-Stage:
    image: bishopdynamics/netbootstudio:latest
    restart: unless-stopped
    ports:
      - "8082:8082"
    # need network_mode: host or mac address lookup wont work correctly
    network_mode: host
    volumes:
      - ${HARDCODED_NS_CONFIGDIR}:/opt/NetbootStudio:ro
      - /etc/timezone:/etc/timezone:ro
    command: >
      /bin/bash -c "echo 'Delaying startup to wait for broker and database';sleep 10;python3 NS_Service_Stage.py -m prod -c /opt/NetbootStudio;"

  NS-TFTP:
    image: bishopdynamics/netbootstudio:latest
    restart: unless-stopped
    ports:
      - "69:69/udp"
    # need network_mode: host for dhcp sniffer to work correctly
    network_mode: host
    cap_add:
      - NET_ADMIN
      - NET_BIND_SERVICE
      - NET_RAW
    volumes:
      - ${HARDCODED_NS_CONFIGDIR}:/opt/NetbootStudio
      - /etc/timezone:/etc/timezone:ro
    command: >
      /bin/bash -c "echo 'Delaying startup to wait for broker and database';sleep 10;python3 NS_Service_TFTP.py -m prod -c /opt/NetbootStudio;"

  NS-WebUI:
    image: bishopdynamics/netbootstudio:latest
    restart: unless-stopped
    ports:
      - "443:443"
      - "80:80"
    cap_add:
      - NET_ADMIN
      - NET_BIND_SERVICE
    volumes:
      - ${HARDCODED_NS_CONFIGDIR}:/opt/NetbootStudio:ro
      - /etc/timezone:/etc/timezone:ro
    command: >
      /bin/bash -c "python3 NS_Service_WebUI.py -m prod -c /opt/NetbootStudio;"

  NS-Database:
    image: mariadb
    restart: unless-stopped
    command: --transaction-isolation=READ-COMMITTED --binlog-format=ROW --innodb-file-per-table=1 --skip-innodb-read-only-compressed
    ports:
      - "3306:3306"
    volumes:
      - /opt/local/database:/var/lib/mysql
      - /etc/timezone:/etc/timezone:ro
      - ${HARDCODED_NS_CONFIGDIR}/certs:/opt/NetbootStudio/certs:ro
    environment:
      - MYSQL_ROOT_PASSWORD=${DB_PASSWORD}
      - MYSQL_PASSWORD=${DB_PASSWORD}
      - MYSQL_DATABASE=netbootstudio
      - MYSQL_USER=${DB_USER}

# Note: depends on /opt/local/broker/config/mosquitto.conf, which is generated by first_time_setup.sh
  NS-Broker:
    image: eclipse-mosquitto:latest
    restart: unless-stopped
    ports:
      - "8883:8883"
      - "8884:8884"
    volumes:
      - /opt/local/broker:/mosquitto
      - /etc/timezone:/etc/timezone:ro
      - ${HARDCODED_NS_CONFIGDIR}/certs:/opt/NetbootStudio/certs:ro

  NS-Samba:
    image: dperson/samba
    restart: unless-stopped
    ports:
      - "137:137/udp"
      - "138:138/udp"
      - "139:139/tcp"
      - "445:445/tcp"
    cap_add:
      - NET_ADMIN
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp
    stdin_open: true
    tty: true
    volumes:
      - ${HARDCODED_NS_CONFIGDIR}:/opt/NetbootStudio:ro
      - /etc/timezone:/etc/timezone:ro
    command: '-s "boot_images;/opt/NetbootStudio/boot_images"'

EOF_DOCKER_COMPOSE
takenote "there. see? that wasnt so hard. what? you cant just remember that whole thing off the top of your head like that? pfff... humans are... nevermind."

takenote "well dude, its been fun, but I'm gonna go ahead and check that \"first_time_setup_complete\" box and take off"
set_flag "first_time_setup_complete" || bail "failed to leave first_time_setup_complete flag!"

takenote "oh, and before i go, check this out. Its a surprise tool that will help us later."
# this will print the info we want about certs and rebooting
check_certs
echo ""
echo "  You also MUST reboot before trying to run Netboot Studio, so will do that right now for you."
echo ""
echo "  First-time setup complete. After reboot, you can deploy Netboot Studio with (as the non-root user):"
echo "    cd NetbootStudio-V2"
echo "    ./deploy.sh"
echo ""

takenote "oh, and let me get that reboot button for you."
takenote "later."

echo "i lied its still broken wtf"
#reboot
