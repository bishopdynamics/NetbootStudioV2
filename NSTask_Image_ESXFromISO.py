#!/usr/bin/env python3
"""
Netboot Studio Task for creating new boot image from VMware ESXi iso
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



class NSTask_Image_ESXFromISO(NSTask_Image_Builder):
    # create ESXi installer boot image from iso
    required_keys = ['name', 'comment', 'arch', 'iso_file', 'create_unattended']  # declare required keys an they will be checked at init
    build_dependencies = [
        'sed', 'grep', '7z', 'find', 'chmod'
    ]

    def __init__(self, paths, mqtt_client, task_payload):
        super().__init__(paths, mqtt_client, task_payload)

    def get_subtasks(self):
        # using an ordered dictionary to preserve order during iteration
        self.subtasks = OrderedDict({
                'check_dependencies': {
                    'description': 'Checking build dependencies',
                    'progress': 1,
                    'function': self.check_dependencies,
                },
                'create_workspace': {
                    'description': 'Creating temporary workspace',
                    'progress': 10,
                    'function': self.create_workspace,
                },
                'extract_iso': {
                    'description': 'Extracting ISO contents',
                    'progress': 20,
                    'function': self.extract_iso,
                },
                'lowercase_files': {
                    'description': 'Converting filenames to lowercase',
                    'progress': 40,
                    'function': self.lowercase_files,
                },
                'create_files': {
                    'description': 'Creating boot files',
                    'progress': 50,
                    'function': self.create_files,
                },
                'correct_perms': {
                    'description': 'Correcting file permissions',
                    'progress': 70,
                    'function': self.correct_perms,
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

    def lowercase_files(self):
        # need all files and folders to be renamed as lowercase
        try:
            # rename folders first
            for filepath in self.workspace.glob('**/*'):
                if filepath.is_dir():
                    rel_path = filepath.relative_to(self.workspace)
                    new_rel_path = str(rel_path).lower()
                    new_full_path = self.workspace.joinpath(new_rel_path)
                    # self.log_msg(f'renaming folder: {str(filepath)} to: {str(new_full_path)}')
                    filepath.rename(new_full_path)
            for filepath in self.workspace.glob('**/*'):
                if filepath.is_file():
                    rel_path = filepath.relative_to(self.workspace)
                    new_rel_path = str(rel_path).lower()
                    new_full_path = self.workspace.joinpath(new_rel_path)
                    # self.log_msg(f'renaming file: {str(filepath)} to: {str(new_full_path)}')
                    filepath.rename(new_full_path)
            return True
        except Exception as ex:
            logging.error('Exception while lowercase_files: %s' % ex)
            return False

    def update_metadata(self):
        # modify metadata fields
        
        try:
            # get release from vmware-esx-base-osl.txt, first line with ESXi in it
            osl_file = self.workspace.joinpath('vmware-esx-base-osl.txt')
            esx_release = ''
            max_lines = 5  # how many lines to check before giving up
            linecount = 0
            with open(osl_file, 'r', encoding='utf-8') as oslf:
                for line in oslf:
                    linecount += 1
                    if linecount >= max_lines:
                        break
                    if 'ESXi' in line:
                        esx_release = line.strip('\n')
                        self.log_msg(f'Found esx release string: {esx_release}')
                        break
            if esx_release == '':
                self.log_error('Failed to discover release string in vmware-esx-base-osl.txt')
            # get build number from boot.cfg, only line with build=
            bootcfgfile = self.workspace.joinpath('boot.cfg')
            esx_build = ''
            max_lines = 15  # how many lines to check before giving up
            linecount = 0
            with open(bootcfgfile, 'r', encoding='utf-8') as bcf:
                for line in bcf:
                    linecount += 1
                    if linecount >= max_lines:
                        break
                    if 'build=' in line:
                        esx_build = line.replace('build=', '').strip('\n')
                        self.log_msg(f'Found esx build string: {esx_build}')
                        break
            if esx_build == '':
                self.log_error('Failed to discover build string in boot.cfg')
            self.bootimage_metadata['release'] = f'{esx_release} {esx_build}'
            self.bootimage_metadata['image_type'] = 'vmware-esx-6'
            self.bootimage_metadata['arch'] = self.task_payload['arch']
            if self.task_payload['comment'] == '':
                self.bootimage_metadata['description'] = f'Auto-generated from iso: {self.task_payload["iso_file"]} on {self.created}'
            else:
                self.bootimage_metadata['description'] = self.task_payload['comment']
            self.bootimage_metadata['source_iso'] = self.task_payload['iso_file']
            if self.task_payload['create_unattended']:
                self.bootimage_metadata['supports_unattended'] = True
                self.bootimage_metadata['stage2_unattended_filename'] = 'stage2-unattended.ipxe'
            return True
        except Exception as ex:
            logging.error('Exception while update_metadata: %s' % ex)
            return False

    def create_files(self):
        # create extra files needed for netboot: netboot.cfg & netboot-unattended.cfg
        try:
            serverip = self.config.get('main', 'netboot_server_ip')
            serverport = self.config.get('stageserver', 'port')
            bootcfgfile = self.workspace.joinpath('efi/boot/boot.cfg')
            netbootcfgfile = self.workspace.joinpath('netboot.cfg')
            bootcfg_lines = []
            bootcfg_lines_new = []
            with open(bootcfgfile, 'r', encoding='utf-8') as bcf:
                for line in bcf.readlines():
                    bootcfg_lines.append(line)
            foundprefix = False
            for line in bootcfg_lines:
                # replace any prefix= line with our actual stage server path
                if 'prefix=' in line:
                    bootcfg_lines_new.append(f'prefix=http://{serverip}:{serverport}/boot_images/{self.boot_image_name}\n')
                    foundprefix = True
                else:
                    # remove any / which would mess up netboot paths
                    bootcfg_lines_new.append(line.replace('/', ''))
            # if the original did not have a prefix= line, then add one
            if not foundprefix:
                bootcfg_lines_new.append(f'prefix=http://{serverip}:{serverport}/boot_images/{self.boot_image_name}')
            with open(netbootcfgfile, 'w', encoding='utf-8') as nbcf:
                nbcf.writelines(bootcfg_lines_new)
            # netboot-unattended.cfg
            if self.task_payload['create_unattended']:
                bootcfg_lines_new_unatt = []
                netbootcfgunattendfile = self.workspace.joinpath('netboot-unattended.cfg')
                unatt_kernel_opt = f'kernelopt=runweasel netdevice=vmnic0 bootproto=dhcp ks=http://{serverip}:{serverport}/unattended.cfg\n'
                for line in bootcfg_lines_new:
                    if 'kernelopt=' in line:
                        bootcfg_lines_new_unatt.append(unatt_kernel_opt)
                    else:
                        bootcfg_lines_new_unatt.append(line)
                with open(netbootcfgunattendfile, 'w', encoding='utf-8') as nbcf:
                    nbcf.writelines(bootcfg_lines_new_unatt)
            return True
        except Exception as ex:
            logging.error('Exception while create_files: %s' % ex)
            return False

    def correct_perms(self):
        # need folders to be a+rx
        try:
            result_chmod = self.run_cmd('find . -type d -exec chmod a+rx {} \;', self.workspace)
            if result_chmod.returncode > 0:
                self.log_error('failed to chmod!')
            return True
        except Exception as ex:
            logging.error('Exception while correct_perms: %s' % ex)
            return False

    def generate_ipxe(self):
        # generate iPXE scripts for normal and unattended (if desired)
        # stage2.ipxe, stage2-unattended.ipxe
        # TODO generate differently for arm64
        stage2ipxe = dedent('''\
        #!ipxe
        # Auto-Generated ipxe script for vmware-6x
        imgfetch ${boot-image-path}/efi/boot/bootx64.efi || goto failed
        imgexec bootx64.efi -c ${boot-image-path}/netboot.cfg || goto failed
        ''')
        stage2unattendedipxe = dedent('''\
        #!ipxe
        # Auto-Generated ipxe script for vmware-6x unattended
        imgfetch ${boot-image-path}/efi/boot/bootx64.efi || goto failed
        imgexec bootx64.efi -c ${boot-image-path}/netboot-unattended.cfg || goto failed
        ''')
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
            'task_type': 'image_esx_installer_from_iso',
            'task_payload': {
                'iso_file': 'esxi7.iso',
                'create_unattended': True,
                'arch': 'amd64',
                'name': 'Jacks vmware test build',
                'comment': 'Testing esx-from-iso',
            },
            'task_id': str(uuid.uuid4()),
            'task_name': 'New VMware ESXi boot image from ISO',
            'task_description': 'Create a new VMware ESXi installer boot image from ISO'
        }
        PATHS_TEST = build_paths('/opt/NetbootStudio')
        taskobj = NSTask_Image_ESXFromISO(PATHS_TEST, send_message, TEST_TASK)
        taskobj.start()

    except Exception as e:
        logging.exception('i had an exception')
