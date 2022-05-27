#!/usr/bin/env bash
# depends on stage4 functions

# set up user james to have sudo with nopasswd

######################## Config

LOCAL_USER_NAME="james"
# lets add some stuff to .profile
cat << EOF >> /etc/sudoers
${LOCAL_USER_NAME} ALL=(ALL) NOPASSWD: ALL
EOF
