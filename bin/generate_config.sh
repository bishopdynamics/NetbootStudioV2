#!/usr/bin/env bash
# Netboot Studio - generate netbootstudio runtime config


source ./bin/nscommon.bashlib || {
  echo "failed to source nscommon.bashlib"
  exit 1
}

# shellcheck disable=SC1091
source "local_environment.sh" || {
  echo "failed to source local_environment.sh"
  exit 1
}

takenote "generating netbootstudio runtime config.ini"

cat << EOF_CONFIG_INI > "${NS_CONFIGDIR}/config.ini"
; auto-generated by Netboot Studio generate_config.sh
[main]
; this is the ip of your netboot server, where all the services will run
netboot_server_ip = ${SERVER_IPADDRESS}
; the hostname of your netboot server
netboot_server_hostname = ${SERVER_HOSTNAME}
; user and group to chown things as
service_user = ${SERVICE_USER}
service_group = ${SERVICE_GROUP}
service_uid = ${SERVICE_UID}
service_gid = ${SERVICE_GID}

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
admin_user = ${WEBUI_ADMIN_USER}
admin_password = ${WEBUI_ADMIN_PASSWORD}

[database]
; these details must match in docker-compose.yml
port = 3306
database = netbootstudio
user = ${SERVICE_USER}
password = ${DB_PASSWORD}

[broker]
; these details must match in docker-compose.yml
port = 8883
port_websocket = 8884
user = ${SERVICE_USER}
password = ${BROKER_PASSWORD}

[samba]
user = ${SERVICE_USER}
password = ${SAMBA_PASSWORD}

[nfs]
user = ${SERVICE_USER}
password = ${NFS_PASSWORD}

EOF_CONFIG_INI