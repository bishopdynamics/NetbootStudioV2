#!/usr/bin/env bash
# depends on stage4 functions

# set up specifics of user james

######################## Config

LOCAL_USER_NAME="james"
LOCAL_USER_GROUP="staff"
# below, in single-quotes, contents of ~/.ssh/id_rsa.pub
SSH_PUBLIC_KEY='ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCuFO0gWrnU1OgGsO4EBX66bumHnGvANIrxzFfQ0YB7DKreJScnHM74qsHbuFIMcMHKnMaB4Eu3V/uJ/uirmOX8YsulKxsVSUG3V2nK+H7A0EjvklagA4dZFhW62vdL5Y6byupdqvqDf5M37zqTg/HZen64ZZlwXodVaBtPDh0CXizjzHR528UwJ0EiBXoldKOtCVRgpTlzN+7uNT2pcfX4xhcVOToBSB1vCsFfg3H6H0r6+UqoIVU7KWuUAdcgUUmuBYFXUm6lvjqKgb1JW93TVGJZQfK0UdozGCn3Rxg+n1XlHlTYzk3TPs0ckSR/Xvmvvx7t/KsfdrTEPD/GSoUImRdJcbbQFKkrcg2rA6z98kMQZW4GITr42UBEPJF+5SS8cWhPIk9NJ76vL0iMEhrV1lfBwlCUf+JM6lg4zpl/q5vlSWpWxuiop6TLz3FMsetrlK4qg4PkAmp5uddiHtINcgoiUrD1G7KkvuFi7agyB6Y+STwSOLoltYKEFDV7PXs= james'

######################## Do Stuff

announce "setting up sudo for $LOCAL_USER_NAME"
add_line_to_file "$LOCAL_USER_NAME"' ALL=(ALL:ALL) ALL' /etc/sudoers

announce "installing ssh public key for $LOCAL_USER_NAME"
mkdir -p /home/${LOCAL_USER_NAME}/.ssh
touch /home/${LOCAL_USER_NAME}/.ssh/authorized_keys
chown ${LOCAL_USER_NAME}:${LOCAL_USER_GROUP} /home/${LOCAL_USER_NAME}/.ssh
add_line_to_file "$SSH_PUBLIC_KEY" /home/${LOCAL_USER_NAME}/.ssh/authorized_keys
chmod 644 /home/${LOCAL_USER_NAME}/.ssh/authorized_keys

announce "creating .profile for ${LOCAL_USER_NAME}"
touch /home/${LOCAL_USER_NAME}/.profile
chown ${LOCAL_USER_NAME}:${LOCAL_USER_NAME} /home/${LOCAL_USER_NAME}/.profile

# lets add some stuff to .profile
cat << 'EOF' >> /home/${LOCAL_USER_NAME}/.profile
export PATH=${HOME}/bin:$PATH
alias ll='ls -1'
alias la='ls -alh'
EOF

