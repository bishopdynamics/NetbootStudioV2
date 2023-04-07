#!/usr/bin/env python3
"""
Netboot Studio Task for creating new boot image from windows iso
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2019-2023 James Bishop (james@bishopdynamics.com)


import logging
import uuid
import pathlib
import json

from textwrap import dedent
from collections import OrderedDict

from NSTasks import NSTask_Image_Builder
from NSCommon import build_paths, get_timestamp, sanitize_string



class NSTask_Image_WindowsFromISO(NSTask_Image_Builder):
    # create windows installer boot image from iso
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

    def update_metadata(self):
        # modify metadata fields
        try:
            self.bootimage_metadata['image_type'] = 'windows-10'
            self.bootimage_metadata['arch'] = self.task_payload['arch']
            if self.task_payload['comment'] == '':
                self.bootimage_metadata['description'] = f'Auto-generated from iso: {self.task_payload["iso_file"]} on {self.created}'
            else:
                self.bootimage_metadata['description'] = self.task_payload['comment']
            self.bootimage_metadata['source_iso'] = self.task_payload['iso_file']
            self.bootimage_metadata['release'] = 'Unknown'
            if self.task_payload['create_unattended']:
                self.bootimage_metadata['supports_unattended'] = True
                self.bootimage_metadata['stage2_unattended_filename'] = 'stage2-unattended.ipxe'
            return True
        except Exception as ex:
            logging.error('Exception while update_metadata: %s' % ex)
            return False

    def create_files(self):
        # create extra files needed for netboot: winpeshl.ini & startnet.cmd
        #   note: mount.cmd is fetched dynamically stage server
        # note that we call cmd.exe after mount.cmd, as a fallback shell in case something fails
        # if startnet.cmd hangs and we close the window, then mount.cmd will fail and close, and then a prompt will appear
        # if mount.cmd hangs and we close the window, then a prompt will appear
        # if mount.cmd works as intended, cmd.exe never gets a chance to run
        # NOTE need to use \r\n so that newlines are correct for 'latin' encoding, which windows uses
        try:
            winpeshlini = dedent('''\
            [LaunchApps]\r\n
            "startnet.cmd"\r\n
            "mount.cmd"\r\n
            "cmd.exe"\r\n
            ''')
            startnetcmd = dedent('''\
            @echo off\r\n
            echo if wpeinit fails, you will be dropped to a command prompt\r\n
            echo this might take a minute...\r\n
            @echo on\r\n
            wpeinit\r\n
            ''')
            # NOTE need to use 'latin' encoding for windows, wt = text mode
            with open(self.workspace.joinpath('winpeshl.ini'), 'wt', encoding='latin') as f:
                f.write(winpeshlini)
            with open(self.workspace.joinpath('startnet.cmd'), 'wt', encoding='latin') as f:
                f.write(startnetcmd)
            return True
        except Exception as ex:
            logging.error('Exception while create_files: %s' % ex)
            return False

    def correct_perms(self):
        # for windows installer to work, all dll & exe files need to be marked executable
        # TODO right now we just make all files a+rx and it works, but thats excessive
        try:
            result_chmod = self.run_cmd('find . -exec chmod a+rx {} \;', self.workspace)
            if result_chmod.returncode > 0:
                self.log_error('failed to chmod!')
            return True
        except Exception as ex:
            logging.error('Exception while correct_perms: %s' % ex)
            return False

    def generate_ipxe(self):
        # generate iPXE scripts for normal and unattended (if desired)
        # stage2.ipxe, stage2-unattended.ipxe
        # we want to load ALL .ini files found in the root of the image, into the ramdisk
        #   this picks up our winpeshl.ini
        #   this also catches tweaks like Hiren's Boot CD
        ini_files = self.workspace.glob('*.ini')
        ini_file_names = []
        for fileobj in ini_files:
            ini_file_names.append(fileobj.name)
        ini_load_lines = ''
        self.log_msg(f'found ini files: {ini_file_names}')
        # detect Hiren's boot cd so we can skip winpeshl.ini
        skip_winpeshl = False
        for ini_file in ini_file_names:
            if ini_file == 'HBCD_PE.ini':
                skip_winpeshl = True
        for ini_file in ini_file_names:
            if ini_file == 'winpeshl.ini' and skip_winpeshl:
                self.log_msg('skipping winpeshl.ini')
                continue
            else:
                ini_load_lines += 'imgfetch ${boot-image-path}/%s %s|| goto failed\n' % (ini_file, ini_file)
        stage2ipxe = '''\
#!ipxe
# Auto-Generated ipxe script for windows installer
imgload ${wimboot-path} || goto failed
imgfetch ${boot-image-path}/boot/fonts/segmono_boot.ttf  segmono_boot.ttf ||
imgfetch ${boot-image-path}/boot/fonts/segoe_slboot.ttf  segoe_slboot.ttf ||
imgfetch ${boot-image-path}/boot/fonts/segoen_slboot.ttf segoen_slboot.ttf ||
imgfetch ${boot-image-path}/boot/fonts/wgl4_boot.ttf     wgl4_boot.ttf ||
imgfetch ${boot-image-path}/startnet.cmd startnet.cmd || goto failed
imgfetch ${windows-mount-cmd-url} mount.cmd || goto failed
# Auto-populated .ini files
%s# End ini files
imgfetch ${boot-image-path}/boot/bcd BCD || goto failed
imgfetch ${boot-image-path}/boot/boot.sdi boot.sdi || goto failed
imgfetch -n boot.wim ${boot-image-path}/sources/boot.wim boot.wim || goto failed
imgexec || goto failed
''' % ini_load_lines
        stage2unattendedipxe = '''\
#!ipxe
# Auto-Generated ipxe script for unattended windows installer
imgload ${wimboot-path} || goto failed
imgfetch ${boot-image-path}/boot/fonts/segmono_boot.ttf  segmono_boot.ttf ||
imgfetch ${boot-image-path}/boot/fonts/segoe_slboot.ttf  segoe_slboot.ttf ||
imgfetch ${boot-image-path}/boot/fonts/segoen_slboot.ttf segoen_slboot.ttf ||
imgfetch ${boot-image-path}/boot/fonts/wgl4_boot.ttf     wgl4_boot.ttf ||
imgfetch ${unattended-url-windows} unattend.xml || goto failed
imgfetch ${boot-image-path}/startnet.cmd startnet.cmd || goto failed
imgfetch ${windows-mount-cmd-url} mount.cmd || goto failed
# Auto-populated .ini files
%s# End ini files
imgfetch ${boot-image-path}/boot/bcd BCD || goto failed
imgfetch ${boot-image-path}/boot/boot.sdi boot.sdi || goto failed
imgfetch -n boot.wim ${boot-image-path}/sources/boot.wim boot.wim || goto failed
imgexec || goto failed
''' % ini_load_lines
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
            'task_type': 'image_windows_installer_from_iso',
            'task_payload': {
                'iso_file': 'Hirens_Boot_CD_PE_x64_v1.0.2.iso',
                'create_unattended': True,
                'arch': 'amd64',
                'name': 'Jacks Hiren Build from ISO',
                'comment': 'Testing windows-from-iso',
            },
            'task_id': str(uuid.uuid4()),
            'task_name': 'New Windows boot image from ISO',
            'task_description': 'Create a new Windows installer boot image from ISO'
        }
        PATHS_TEST = build_paths('/opt/NetbootStudio')
        taskobj = NSTask_Image_WindowsFromISO(PATHS_TEST, send_message, TEST_TASK)
        taskobj.start()

    except Exception as e:
        logging.exception('i had an exception')
