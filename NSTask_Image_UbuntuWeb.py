#!/usr/bin/env python3
"""
Netboot Studio Task for creating new boot image for Ubuntu webinstaller
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2019-2023 James Bishop (james@bishopdynamics.com)


import logging
import uuid
import pathlib
import shutil
import re

from textwrap import dedent
from collections import OrderedDict

from NSTasks import NSTask_Image_Builder
from NSCommon import build_paths, get_timestamp, sanitize_string



class NSTask_Image_UbuntuWeb(NSTask_Image_Builder):
    # create Ubuntu webinstaller boot image
    required_keys = ['name', 'comment', 'ubuntu_release', 'kernel_args', 'create_unattended']  # declare required keys an they will be checked at init
    build_dependencies = []

    def __init__(self, paths, mqtt_client, task_payload):
        super().__init__(paths, mqtt_client, task_payload)

    def get_subtasks(self):
        # using an ordered dictionary to preserve order during iteration
        self.subtasks = OrderedDict({
                'create_workspace': {
                    'description': 'Creating temporary workspace',
                    'progress': 10,
                    'function': self.create_workspace,
                },
                'generate_ipxe': {
                    'description': 'Generating iPXE scripts',
                    'progress': 80,
                    'function': self.generate_ipxe,
                },
                'update_metadata': {
                    'description': 'Updating metadata',
                    'progress': 85,
                    'function': self.update_metadata,
                },
                'write_metadata': {
                    'description': 'Writing metadata.yaml',
                    'progress': 90,
                    'function': self.write_metadata,
                },
                'finalize_and_cleanup': {
                    'description': 'Finalizing',
                    'progress': 95,
                    'function': self.finalize_and_cleanup,
                },
        })
        return self.subtasks

    def update_metadata(self):
        # modify metadata fields
        try:
            self.bootimage_metadata['release'] = self.task_payload['ubuntu_release']
            self.bootimage_metadata['image_type'] = 'ubuntu-webinstaller'
            self.bootimage_metadata['arch'] = 'none'
            if self.task_payload['comment'] == '':
                self.bootimage_metadata['description'] = f'Auto-generated on {self.created}'
            else:
                self.bootimage_metadata['description'] = self.task_payload['comment']
            if self.task_payload['create_unattended']:
                self.bootimage_metadata['supports_unattended'] = True
                self.bootimage_metadata['stage2_unattended_filename'] = 'stage2-unattended.ipxe'
            return True
        except Exception as ex:
            logging.error('Exception while update_metadata: %s' % ex)
            return False

    def generate_ipxe(self):
        # generate iPXE scripts for normal and unattended (if desired)
        # stage2.ipxe, stage2-unattended.ipxe
        stage2ipxe = dedent('''\
        set ubuntu-release %s
        set boot-image-path ${ubuntu-mirror}/dists/${ubuntu-release}/main/installer-${arch}/current/images/netboot/ubuntu-installer/${arch}
        set extra-kernel-args %s
        iseq ${arch} arm64 && set extra-kernel-args ${extra-kernel-args} console=tty1 console=ttyS2,1500000 ||
        set this-image-args initrd=initrd.gz vga=788 debian-installer/locale=en_US keymap=us hw-detect/load_firmware=false --- ${extra-kernel-args}
        imgfree
        imgfetch ${boot-image-path}/linux || goto failed
        imgfetch ${boot-image-path}/initrd.gz || goto failed
        imgload linux || goto failed
        imgargs linux ${this-image-args} || goto failed
        imgexec || goto failed
        ''' % (self.task_payload['ubuntu_release'], self.task_payload['kernel_args']))

        stage2unattendedipxe = dedent('''\
        set ubuntu-release %s
        set boot-image-path ${ubuntu-mirror}/dists/${ubuntu-release}/main/installer-${arch}/current/images/netboot/ubuntu-installer/${arch}
        set extra-kernel-args %s
        iseq ${arch} arm64 && set extra-kernel-args ${extra-kernel-args} console=tty1 console=ttyS2,1500000 ||
        set this-image-args initrd=initrd.gz vga=788 debian-installer/locale=en_US keymap=us hw-detect/load_firmware=false hostname=unassigned-hostname domain=unassigned-domain auto url=${unattended-url-linux} --- ${extra-kernel-args}
        imgfree
        imgfetch ${boot-image-path}/linux || goto failed
        imgfetch ${boot-image-path}/initrd.gz || goto failed
        imgload linux || goto failed
        imgargs linux ${this-image-args} || goto failed
        imgexec || goto failed
        ''' % (self.task_payload['ubuntu_release'], self.task_payload['kernel_args']))
        try:
            with open(self.workspace.joinpath('stage2.ipxe'), 'wt', encoding='utf-8') as f:
                f.write(stage2ipxe)
            if self.task_payload['create_unattended']:
                with open(self.workspace.joinpath('stage2-unattended.ipxe'), 'wt', encoding='utf-8') as f:
                    f.write(stage2unattendedipxe)
            return True
        except Exception as ex:
            logging.error('Exception while generate_ipxe: %s' % ex)
            return False


# all tasks should include a section like this to facilitate standalone testing
if __name__ == "__main__":
    CUR_PATH = pathlib.Path(__file__).parent.absolute()
    print('current path: %s' % CUR_PATH)
    LOG_LEVEL = 'DEBUG'
    LOG_FORMAT = '%(asctime)-15s %(threadName)-10s %(module)-13s:%(lineno)-3d %(funcName)-24s %(levelname)s - %(message)s'
    logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)

    def send_message(message: dict):
        # print('would have sent update: %s' % json.dumps(message))
        return

    try:
        TEST_TASK = {
            'task_type': 'image_ubuntu_webinstaller',
            'task_payload': {
                'create_unattended': True,
                'ubuntu_release': 'bionic',
                'name': 'Jacks ubuntu webinstaller test build',
                'kernel_args': '',
                'comment': 'Testing ubuntu-webinstaller',
            },
            'task_id': str(uuid.uuid4()),
            'task_name': 'New Ubuntu Webinstaller boot image',
            'task_description': 'Create a new Ubuntu Web installer boot image'
        }
        PATHS_TEST = build_paths('/opt/NetbootStudio')
        taskobj = NSTask_Image_UbuntuWeb(PATHS_TEST, send_message, TEST_TASK)
        taskobj.start()

    except Exception as e:
        logging.exception('i had an exception')
