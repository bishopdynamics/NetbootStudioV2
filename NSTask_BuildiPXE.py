#!/usr/bin/env python3
"""
Netboot Studio Task for building ipxe binaries
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2021 James Bishop (james@bishopdynamics.com)


import os
import platform
import logging
import uuid
import json
import tempfile
import pathlib
import shutil
import subprocess
import hashlib

from collections import OrderedDict

from NSTasks import NSTask
from NSCommon import build_paths, get_timestamp

# TODO we can build wimboot: https://github.com/ipxe/wimboot/blob/master/.github/workflows/build.yml
# TODO we can build for raspberrypi: https://github.com/ipxe/pipxe
# TODO need to cross-compile for amd64 if on arm64 host (rocklobster host!)


class NSTask_BuildiPXE(NSTask):
    # manage building ipxe binaries
    required_keys = ['name', 'comment', 'commit_id', 'arch', 'stage1_file']  # declare required keys an they will be checked at init
    ipxe_build_targets = {
        'amd64': {
            'bin-x86_64-efi/ipxe.efi': 'ipxe.efi',
            'bin-x86_64-efi/ipxe.usb': 'ipxe.iso',
        },
        'arm64': {
            'bin-arm64-efi/ipxe.efi': 'ipxe.efi',
            'bin-arm64-efi/ipxe.usb': 'ipxe.iso',
        }
    }
    url_ipxe = 'https://github.com/ipxe/ipxe'  # ipxe git repo (github version handles traffic better)
    ipxe_default_commit = '988d2c1'  # commit id to default to, if none specified. this is Dec 31, 2020 which is the latest stable release as of Oct 2021
    build_dependencies = [
        'make', 'git', 'sed', 'grep',
        'mformat', 'perl', 'genisoimage',
        'unzip', 'wget', 'awk', 'md5sum'
    ]
    build_dep_help = 'try running: sudo apt install build-essential git sed grep mtools perl genisoimage liblzma-dev syslinux binutils unzip isolinux'
    build_args = '-j4'  # arguments to pass to make, as one string NOT a list
    builtin_ipxe_stage1_file = 'netboot-studio-stage1.ipxe'
    build_options = {
        'common': {
            'enable': [
                ('DOWNLOAD_PROTO_HTTPS', 'general.h'),
                ('DOWNLOAD_PROTO_NFS', 'general.h'),
                ('PCI_CMD', 'general.h'),
                ('IMAGE_PNG', 'general.h'),
                ('CONSOLE_CMD', 'general.h'),
                ('IPSTAT_CMD', 'general.h'),
                ('PING_CMD', 'general.h'),
                ('NSLOOKUP_CMD', 'general.h'),
                ('IMAGE_TRUST_CMD', 'general.h'),
                ('TIME_CMD', 'general.h'),
                ('REBOOT_CMD', 'general.h'),
                ('POWEROFF_CMD', 'general.h'),
                ('VLAN_CMD', 'general.h'),
                ('LOTEST_CMD', 'general.h'),
                ('PROFSTAT_CMD', 'general.h'),
                ('IMAGE_EFI', 'general.h'),
                ('NTP_CMD', 'general.h'),
                ('TIME_CMD', 'general.h'),
                ('CERT_CMD', 'general.h'),
                ('IMAGE_GZIP', 'general.h'),
                ('IMAGE_ZLIB', 'general.h'),
                ('PARAM_CMD', 'general.h'),
                ('IMAGE_ARCHIVE_CMD', 'general.h'),
                ('CONSOLE_FRAMEBUFFER', 'console.h'),
                ('CONSOLE_EFI', 'console.sh'),
                ('CONSOLE_SERIAL', 'console.sh'),
            ],
            'disable': [
                ('NET_PROTO_IPV6', 'general.h'),
            ],
        },
        'amd64': {
            'enable': [],
            'disable': [],
        },
        'arm64': {
            'enable': [
                ('NAP_NULL', 'nap.h'),
            ],
            'disable': [
                ('NAP_PCBIOS', 'nap.h'),
                ('NAP_EFIX86', 'nap.h'),
                ('NAP_EFIARM', 'nap.h'),
                ('USB_HCD_XHCI', 'usb.h'),
                ('USB_HCD_EHCI', 'usb.h'),
                ('USB_HCD_UHCI', 'usb.h'),
                ('USB_KEYBOARD', 'usb.h'),
                ('USB_BLOCK', 'usb.h'),
                ('USB_EFI', 'usb.h'),
                ('NET_PROTO_IPV6', 'general.h'),
            ],
        },
    }

    # TODO hardcoded serial port speed here
    # TODO log level doesnt work, doesnt like you defining it again
    build_fixes = {
        'amd64': [
            # TODO do we still need this? i think its specific to pcbios not efi
            'echo  "CFLAGS   += -fno-pie" >> arch/x86/Makefile.pcbios',
            'echo  "LDFLAGS  += -no-pie" >> arch/x86/Makefile.pcbios',
            'echo "#undef COMSPEED" >> config/local/serial.h',
            'echo "#define COMSPEED 1000000" >> config/local/serial.h',
            'echo "#undef LOG_LEVEL" >> config/local/serial.h',
            'echo "#define LOG_LEVEL LOG_ALL" >> config/local/serial.h',
        ],
        'arm64': [
            'echo "#undef COMSPEED" >> config/local/serial.h',
            'echo "#define COMSPEED 1000000" >> config/local/serial.h',
            'echo "#undef LOG_LEVEL" >> config/local/serial.h',
            'echo "#define LOG_LEVEL LOG_ALL" >> config/local/serial.h',
        ],
    }

    def __init__(self, paths, mqtt_client, task_payload):
        super().__init__(paths, mqtt_client, task_payload)
        self.builds_base = self.paths['ipxe_builds']
        self.ssl_ca_cert = self.paths['ssl_ca_cert']
        self.ssl_full_chain = self.paths['ssl_full_chain']
        self.build_id = str(uuid.uuid4())
        self.build_dir = self.builds_base.joinpath(self.build_id)
        self.log_file = self.build_dir.joinpath('build.log')
        # these will get updated later
        self.ipxe_repo = None
        self.commit_id = None
        self.build_targets = None
        self.target_arch = None
        self.stage1_filename = None
        self.stage1_file = None
        self.temp_dir = None
        self.workspace = None
        self.commit_data = None
        self.build_timestamp = None

    def get_subtasks(self):
        # using an ordered dictionary to preserve order during iteration
        self.subtasks = OrderedDict({
                'check_dependencies': {
                    'description': 'Checking build dependencies',
                    'progress': 1,
                    'function': self.check_dependencies,
                },
                'setup_build_info': {
                    'description': 'Setting up build information',
                    'progress': 3,
                    'function': self.setup_build_info
                },
                'get_ipxe_repo': {
                    'description': 'Cloning ipxe repo',
                    'progress': 15,
                    'function': self.get_ipxe_repo,
                },
                'apply_build_options': {
                    'description': 'Applying Build Options',
                    'progress': 25,
                    'function': self.apply_build_options,
                },
                'apply_build_fixes': {
                    'description': 'Applying Build Fixes',
                    'progress': 30,
                    'function': self.apply_build_fixes,
                },
                'build_all_targets': {
                    'description': 'Building All Targets',
                    'progress': 75,
                    'function': self.build_all_targets,
                },
                'write_metadata': {
                    'description': 'Writing Metadata',
                    'progress': 80,
                    'function': self.write_metadata,
                },
                'calculate_checksums': {
                    'description': 'Calculating Checksums',
                    'progress': 95,
                    'function': self.calculate_checksums,
                }
        })
        return self.subtasks

    # subtask methods
    def check_dependencies(self):
        # check that each of the commmands we need are available
        # this assumes we running in the docker container
        missing_deps = []
        logging.debug('checking dependencies')
        if platform.system() != 'Linux':
            logging.error('only support building ipxe binaries on Linux host')
            return False
        for _dep in self.build_dependencies:
            result = self.run_cmd('command -v %s' % _dep, skip_logfile=True)
            if result.returncode > 0:
                missing_deps.append(_dep)
        if missing_deps:
            logging.error('ipxe build needs some commands which are missing: %s' % str(missing_deps))
            logging.error('  %s' % self.build_dep_help)
            return False
        else:
            return True

    def setup_build_info(self):
        try:
            self.stage1_filename = self.task_payload['stage1_file']
            if self.stage1_filename == 'default':
                # special default returns the built-in one (the one that lives in program folder)
                self.stage1_file = pathlib.Path(self.paths['program_base']).joinpath(self.builtin_ipxe_stage1_file)
            else:
                self.stage1_file = pathlib.Path(self.paths['stage1_files']).joinpath(self.stage1_filename)
            if not self.stage1_file.is_file():
                self.log_error('stage1 file does not exist: %s' % self.stage1_file)
            # since build_dir is created here, we can now startusing log_msg and log_error
            os.makedirs(self.build_dir, exist_ok=False)
            logging.debug('build log file: %s' % self.log_file)
            self.log_msg('Starting build at %s' % self.task_timestamp_start)
            self.target_arch = self.task_payload['arch']
            if self.target_arch not in self.ipxe_build_targets:
                self.log_error('dont know how to build ipxe for arch: %s' % self.target_arch)
            self.commit_id = self.task_payload['commit_id']
            self.build_targets = self.ipxe_build_targets[self.target_arch]
            self.build_timestamp = get_timestamp()
            return True
        except Exception:
            return False

    def get_ipxe_repo(self):
        # clone the ipxe repo and checkout the given commit id
        try:
            # TODO self.temp_dir.cleanup()
            self.temp_dir = tempfile.TemporaryDirectory()
            self.workspace = pathlib.Path(self.temp_dir.name)
            self.commit_data = {'id': self.commit_id, 'url': self.url_ipxe}
            result_clone = self.run_cmd('git clone %s' % self.url_ipxe, self.workspace)
            ipxe_git_repo = self.workspace.joinpath('ipxe')
            if result_clone.returncode > 0:
                self.log_error('failed to clone ipxe repo!')
            #  git log --graph --pretty=format:'%h,%ci'|grep 075f9e0|cut -c11-
            #  075f9e0,2021-01-25 00:31:23 -0800
            commit_timestamp = self.run_cmd('git log --graph --pretty=format:\'%%h,%%ci\'|grep %s|cut -c12-' % self.commit_data['id'], ipxe_git_repo)
            self.commit_data['timestamp'] = commit_timestamp.stdout.strip()
            self.log_msg('checking out commit %s (%s)' % (self.commit_data['id'], self.commit_data['timestamp']))
            result_checkout = self.run_cmd('git checkout %s' % self.commit_data['id'], ipxe_git_repo)
            if result_checkout.returncode > 0:
                self.log_error('failed to check out commit: %s' % self.commit_data['id'])
            self.ipxe_repo = ipxe_git_repo.joinpath('src')
            return True
        except Exception as ex:
            logging.exception('some exception while get_ipxe_repo: %s' % ex)
            return False

    def apply_build_options(self):
        # apply all the build options
        self.log_msg('applying ipxe build options for arch: %s' % self.target_arch)
        success = True
        for (option, filename) in self.build_options['common']['enable']:
            result = self.enable_build_option(option, filename)
            if not result:
                success = False
                break
        for (option, filename) in self.build_options['common']['disable']:
            result = self.disable_build_option(option, filename)
            if not result:
                success = False
                break
        for (option, filename) in self.build_options[self.target_arch]['enable']:
            result = self.enable_build_option(option, filename)
            if not result:
                success = False
                break
        for (option, filename) in self.build_options[self.target_arch]['disable']:
            result = self.disable_build_option(option, filename)
            if not result:
                success = False
                break
        return success

    def apply_build_fixes(self):
        # apply all our ghetto build fixes
        self.log_msg('applying ipxe build fixes for arch: %s' % self.target_arch)
        success = True
        for fixcmd in self.build_fixes[self.target_arch]:
            f_result = self.run_cmd(fixcmd, self.ipxe_repo)
            if f_result.returncode != 0:
                success = False
                break
        return success

    def build_all_targets(self):
        try:
            for target, resultfile in self.build_targets.items():
                self.log_msg('building ipxe target: %s -> %s' % (target, resultfile))
                build_command = 'make -k %s %s "EMBED=%s" "CERT=%s" "TRUST=%s" ' % (self.build_args, target, self.stage1_file, self.ssl_full_chain, self.ssl_ca_cert)
                build_command_nomenu = 'make -k %s %s "CERT=%s" "TRUST=%s" ' % (self.build_args, target, self.ssl_full_chain, self.ssl_ca_cert)
                if self.target_arch == 'amd64':
                    build_command += ''  # nothing to add for amd64
                    build_command_nomenu += ''
                elif self.target_arch == 'arm64':
                    build_command += '"CROSS_COMPILE=aarch64-linux-gnu-" "ARCH=arm64" '
                    build_command_nomenu += '"CROSS_COMPILE=aarch64-linux-gnu-" "ARCH=arm64" '
                b_result = self.run_cmd(build_command, self.ipxe_repo)
                if b_result.returncode > 0:
                    self.log_error('failed ipxe build for target: %s' % target)
                else:
                    w_file = self.ipxe_repo.joinpath(target)
                    if not shutil.copyfile(w_file, self.build_dir.joinpath(resultfile)):
                        self.log_error('failed to copy built file into build_dir')
                    else:
                        if resultfile == 'ipxe.iso':
                            # also build nomenu artifacts for iso
                            b_result = self.run_cmd(build_command_nomenu, self.ipxe_repo)
                            resultfile = 'ipxe-nomenu.iso'
                            if b_result.returncode > 0:
                                self.log_error('failed ipxe nomenu build for target: %s' % target)
                            else:
                                w_file = self.ipxe_repo.joinpath(target)
                                if not shutil.copyfile(w_file, self.build_dir.joinpath(resultfile)):
                                    self.log_error('failed to copy built nomenu file into build_dir')
            # end for loop
            return True
        except Exception as ex:
            logging.error('Exception while build_all_targets: %s' % ex)
            return False

    def write_metadata(self):
        try:
            self.log_msg('writing metadata.json')
            meta_file = self.build_dir.joinpath('metadata.json')
            metadata = {
                'build_id': self.build_id,
                'commit_id': self.task_payload['commit_id'],
                'build_timestamp': self.build_timestamp,
                'build_name': self.task_payload['name'],
                'stage1': self.task_payload['stage1_file'],
                'comment': self.task_payload['comment'],
                'arch': self.task_payload['arch'],
            }
            metadata_string = json.dumps(metadata)
            with open(meta_file, 'w') as mf:
                mf.write(metadata_string)
            return True
        except Exception:
            logging.exception('Unexpected exception while writing metadata.json')
            return False

    def calculate_checksums(self):
        # calculate checksums for all files, and generate checksums.txt
        self.log_msg('generating checksums for ipxe artifacts')
        try:
            with open(self.build_dir.joinpath('checksums.txt'), 'a') as checksumfile:
                for filename in os.listdir(self.build_dir):
                    if filename == 'checksums.txt':
                        continue  # skip checksums file itself
                    full_filename = self.build_dir.joinpath(filename)
                    this_hash = hashlib.md5(open(full_filename, 'rb').read()).hexdigest()
                    this_line = '%s %s\n' % (filename, this_hash)
                    checksumfile.write(this_line)
            return True
        except Exception as ex:
            logging.exception('failed to calculate checksums: %s' % ex)
            return False

    # helper methods
    def enable_build_option(self, build_option, file_name):
        # enable a build option by name
        self.log_msg('enabling ipxe build option: %s in file: %s' % (build_option, file_name))
        en_result = self.run_cmd('echo "#define %s" >> "config/local/%s"' % (build_option, file_name), self.ipxe_repo)
        if en_result.returncode > 0:
            self.log_msg('failed to enable ipxe build option: %s in file %s' % (build_option, file_name), error=True)
            return False
        else:
            return True

    def disable_build_option(self, build_option, file_name):
        # disable a build option by name
        self.log_msg('disabling ipxe build option: %s in file: %s' % (build_option, file_name))
        en_result = self.run_cmd('echo "#undef %s" >> "config/local/%s"' % (build_option, file_name), self.ipxe_repo)
        if en_result.returncode > 0:
            self.log_msg('failed to disable ipxe build option: %s in file %s' % (build_option, file_name), error=True)
            return False
        else:
            return True

    def run_cmd(self, cmd, cwd=None, skip_logfile=False):
        # given a string representing command and arguments, run it and return an object you can deal with
        # the only purpose of this is to provide a single place to change our approach to running commands
        # subprocess.run() does not raise an exception if the underlying process errors!
        # shell=True is needed so that command -v works. It is a security risk, we should move as many things to pythony instead of bashy
        # we redirect stderr to stdout, so that both are in the same output and in order
        if not skip_logfile:
            self.log_msg('running command:[%s] %s' % (cwd, cmd))
        result = subprocess.run('%s 2>&1' % cmd, shell=True, universal_newlines=True, cwd=cwd, capture_output=True, text=True)
        output = result.stdout
        if not skip_logfile:
            self.log_msg(output)
        if result.returncode != 0:
            if not skip_logfile:
                raise Exception('run_cmd failed, check log file: %s' % self.log_file)
            else:
                raise Exception('run_cmd failed and wasnt logged to a file')
        return result

    def log_msg(self, msg, error=False):
        # write some text to the log file, followed by a blank line
        #   also print the message
        if error:
            logging.error('NSTask_build_ipxe error: %s' % msg)
        with open(self.log_file, 'a+') as lf:
            lf.write(msg)
            lf.write('\n\n')

    def log_error(self, msg):
        # log an error to the file, also throw an exception (so use this in a try block)
        self.log_msg(msg, error=True)
        raise Exception(msg)


# all tasks should include a section like this to facilitate standalone testing
if __name__ == "__main__":
    CUR_PATH = pathlib.Path(__file__).parent.absolute()
    print('current path: %s' % CUR_PATH)
    LOG_LEVEL = 'DEBUG'
    LOG_FORMAT = '%(asctime)-15s %(threadName)-10s %(module)-13s:%(lineno)-3d %(funcName)-24s %(levelname)s - %(message)s'
    logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)

    def send_message(message: dict):
        print('would have sent update: %s' % json.dumps(message))

    try:
        TEST_TASK = {
            'task_type': 'build_ipxe',
            'task_payload': {
                'stage1_file': 'default',
                'commit_id': 'e6f9054',
                'arch': 'amd64',
                'name': 'Jackbuild2',
                'comment': 'i am jacks second favorite build',
            },
            'task_id': str(uuid.uuid4()),
            'task_name': 'Build iPXE',
            'task_description': 'Build an ipxe binary and iso, and another iso without embedded stage1_file'
        }
        PATHS_TEST = build_paths('/opt/NetbootStudio')
        taskobj = NSTask_BuildiPXE(PATHS_TEST, send_message, TEST_TASK)
        taskobj.start()

    except Exception as e:
        logging.exception('i had an exception')
