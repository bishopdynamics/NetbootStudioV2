#!/usr/bin/env python3
"""
Netboot Studio Task for creating new boot image for Debian Live
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2019-2023 James Bishop (james@bishopdynamics.com)

import os
import stat
import logging
import uuid
import pathlib
import shutil
import platform

from textwrap import dedent
from collections import OrderedDict

from NSTasks import NSTask_Image_Builder
from NSCommon import build_paths, get_timestamp, sanitize_string



class NSTask_Image_DebianLive(NSTask_Image_Builder):
    # create Debian live boot image
    required_keys = ['name', 'comment', 'debian_release', 'arch', 'kernel_args', 'include_xfce', 'packages', 'mirror']  # declare required keys an they will be checked at init
    build_dependencies = ['lb', 'debootstrap']
    kernel_name = 'vmlinuz'
    initrd_name = 'initrd.img'
    squashfs_name = 'filesystem.squashfs'

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
                    'description': 'Creating workspace',
                    'progress': 10,
                    'function': self.create_workspace,
                },
                'create_scratch': {
                    'description': 'Creating scratch',
                    'progress': 15,
                    'function': self.create_scratch,
                },
                'prepare_config': {
                    'description': 'Preparing config to build liveimage',
                    'progress': 40,
                    'function': self.prepare_config,
                },
                'build_image': {
                    'description': 'Building liveimage',
                    'progress': 60,
                    'function': self.build_image,
                },
                'collect_files': {
                    'description': 'Collecting files',
                    'progress': 70,
                    'function': self.collect_files,
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

    def prepare_config(self):
        # prepare config for building liveimage

        # this maps what platform.machine() returns to what we use in netboot studio
        arch_map_platform = {
            'x86_64': 'amd64',
            'amd64': 'amd64',
            'aarch64': 'arm64',
            'arm64': 'arm64',
        }
        # this maps to how qemu-X-static binaries are named
        arch_map_qemu_static = {
            'arm64': 'aarch64',
            'arm32': 'arm',
            'arm': 'arm',
            'aarch64': 'aarch64',
            'amd64': 'x86_64',
            'x86_64': 'x86_64',
            'x86': 'i386',
            'i386': 'i386',
            'i486': 'i386',
            'i586': 'i386',
            'i686': 'i386',
            'ppc': 'ppc',
            'ppc32': 'ppc',
            'ppc64': 'ppc64',
        }
        try:
            linux_flavor = self.task_payload['arch']  # for our use-case, flavor always matches arch
            config_arch = self.task_payload['arch']
            config_mirror = self.task_payload['mirror']
            config_distro = self.task_payload['debian_release']
            config_installer = self.task_payload['debian_installer']
            config_archive_areas = self.task_payload['archive_areas']
            host_arch = arch_map_platform[platform.machine()]
            dir_auto = self.scratch.joinpath('auto')
            dir_auto.mkdir()
            file_auto_config = dir_auto.joinpath('config')
            file_auto_build = dir_auto.joinpath('build')
            file_auto_clean = dir_auto.joinpath('clean')

            #  LB Config Arguments
            #   --mode "debian" \\  # debian or ubuntu
            #   --distribution "{config_distro}" \\
            #   --architectures "{config_arch}" \\
            #   --linux-flavours "{linux_flavor}" \\
            #   --binary-images "netboot" \\  # type of image to build: iso / iso-hybrid / netboot / tar / hdd
            #   --mirror-binary "{config_mirror}" \\  # the repo mirror to use
            #   --archive-areas "main" \\  # here you could include contrib and non-free
            #   --chroot-filesystem "squashfs" \\  # ext4 / squashfs / jffs2 / none
            #   --debian-installer false \\  # type of debian-installer to include: true / false / cdrom / netinst / netboot / businesscard / live / false
            #   --apt-indices false \\  # remove apt indexes
            #   --apt-source-archives false \\  # dont include deb-src entries in apt lists
            #   --memtest none \\  # remove memtest


            self.log_msg('writing auto/config')
            self.write_to_file(file_auto_config, dedent(f'''\
            #!/bin/sh
            set -e
            lb config noauto \\
                --mode "debian" \\
                --distribution "{config_distro}" \\
                --architectures "{config_arch}" \\
                --linux-flavours "{linux_flavor}" \\
                --binary-images "netboot" \\
                --mirror-binary "{config_mirror}" \\
                --archive-areas "{config_archive_areas}" \\
                --chroot-filesystem "squashfs" \\
                --debian-installer "{config_installer}" \\
                --apt-indices false \\
                --apt-source-archives false \\
                --memtest none \\
            '''))
            # if we are building a foreign arch, try to find qemu-static for that arch
            if host_arch != config_arch:
                qemu_arch = arch_map_qemu_static[config_arch]
                qemu_binary = f'/usr/bin/qemu-{qemu_arch}-static'
                if pathlib.Path(qemu_binary).is_file():
                    self.log_msg(f'Building foreign arch: {config_arch} on {host_arch}, using: {qemu_binary}')
                    self.append_to_file(file_auto_config, f'    --bootstrap-qemu-arch "{config_arch}" \\\n')
                    self.append_to_file(file_auto_config, f'    --bootstrap-qemu-static "{qemu_binary}" \\\n')
                else:
                    self.log_error(f'Building foreign arch: {config_arch} on {host_arch}, but unable to find: {qemu_binary}')
            else:
                self.log_msg('building for same arch as host, no qemu required')
            # last line of config
            self.append_to_file(file_auto_config, '    "${@}"\n')

            # create auto/build
            self.log_msg('writing auto/build')
            self.write_to_file(file_auto_build, dedent('''\
            #!/bin/sh
            set -e
            lb build noauto "${@}" 2>&1
            '''))

            # create auto/clean
            self.log_msg('writing auto/clean')
            self.write_to_file(file_auto_clean, dedent('''\
            #!/bin/sh
            set -e
            lb clean noauto "${@}"
            rm -f config/binary config/bootstrap config/chroot config/common config/source
            rm -f build.log
            '''))

            # make auto/ scripts executable
            os.chmod(file_auto_build, stat.S_IRWXO | stat.S_IRWXG |stat.S_IRWXU)
            os.chmod(file_auto_clean, stat.S_IRWXO | stat.S_IRWXG |stat.S_IRWXU)
            os.chmod(file_auto_config, stat.S_IRWXO | stat.S_IRWXG |stat.S_IRWXU)

            # run the configure command
            self.log_msg('running config stage to finish generating config')
            self.run_cmd('lb config', self.scratch)
            
            # configure packages
            # echo "htop fdisk parted u-boot-tools nfs-common xfsprogs lm-sensors hfsplus hfsutils iotop iftop pv wget curl file" >> config/package-lists/my.list.chroot
            packages_base = 'htop fdisk parted u-boot-tools nfs-common xfsprogs lm-sensors hfsplus hfsutils iotop iftop pv wget curl file'
            packages_xfce = 'task-xfce-desktop firefox-esr gparted'
            file_packages = self.scratch.joinpath('config/package-lists/my.list.chroot')
            self.append_to_file(file_packages, packages_base)
            if self.task_payload['include_xfce']:
                self.append_to_file(file_packages, ' ')  # need space after existing
                self.append_to_file(file_packages, packages_xfce)
            if self.task_payload['packages'] != '':
                self.append_to_file(file_packages, ' ')  # need space after existing
                self.append_to_file(file_packages, self.task_payload['packages'])
            self.append_to_file(file_packages, '\n')  # newline at end of file
            self.scratch.joinpath('chroot').mkdir()
            self.scratch.joinpath('tftpboot').mkdir()
            return True
        except Exception as ex:
            logging.error('Exception while prepare_config: %s' % ex)
            return False

    def attempt_unmount(self, mountpath):
        # try to unmount a given path, relative to scratch, but dont care if fail
        self.log_msg(f'Attempting to unmount {mountpath}')
        try:
            self.run_cmd(f'mountpoint {mountpath} && umount {mountpath}', self.scratch, skip_logfile=True)
            self.log_msg(f'Successfully unmounted {mountpath}')
        except Exception as ex:
            self.log_msg(f'Failed to unmount {mountpath}')
            pass

    def build_image(self):
        # build liveimage
        try:
            self.run_cmd('lb build', self.scratch)
            return True
        except Exception as ex:
            logging.error('Exception while build_image: %s' % ex)
            logging.warning('Attempting to unmount any leftover mounts in chroot')
            # TODO the right way is to somehow find ALL mountpoints under chroot/ and then use that list
            self.attempt_unmount('chroot/dev/pts')
            self.attempt_unmount('chroot/sys')
            self.attempt_unmount('chroot/proc')
            return False

    def collect_files(self):
        # collect the files we need from the build in scratch folder
        try:
            if not self.scratch.joinpath(f'binary/live/{self.squashfs_name}').is_file():
                self.log_error(f'Could not find squashfs: {self.squashfs_name} build must have failed!')
            # the glob business below is needed because 
            #   arm64 builds end up with a whole kernel version appended, 
            #   while amd64 builds are just vmlinuz and initrd.img
            if not self.scratch.joinpath(f'tftpboot/live/{self.kernel_name}').is_file():
                self.log_msg(f'did not find tftpboot/live/{self.kernel_name}, looking for one with build attached')
                found_kernel = None
                # ugly way to get first from a generator
                for result in self.scratch.joinpath(f'tftpboot/live').glob(f'{self.kernel_name}*'):
                    found_kernel = result
                    break
                if found_kernel is not None:
                    self.log_msg(f'found: {found_kernel}')
                    shutil.move(found_kernel, self.scratch.joinpath(f'tftpboot/live/{self.kernel_name}'))
                else:
                    self.log_error(f'failed to find kernel with name: {self.kernel_name}')
            if not self.scratch.joinpath(f'tftpboot/live/{self.initrd_name}').is_file():
                self.log_msg(f'did not find tftpboot/live/{self.initrd_name}, looking for one with build attached')
                found_initrd = None
                # ugly way to get first from a generator
                for result in self.scratch.joinpath(f'tftpboot/live').glob(f'{self.initrd_name}*'):
                    found_initrd = result
                    break
                if found_initrd is not None:
                    self.log_msg(f'found: {found_initrd}')
                    shutil.move(found_initrd, self.scratch.joinpath(f'tftpboot/live/{self.initrd_name}'))
                else:
                    self.log_error(f'failed to find initrd with name: {self.initrd_name}')
            # finally, copy the files we need
            shutil.copy(self.scratch.joinpath(f'tftpboot/live/{self.kernel_name}'), self.workspace.joinpath(self.kernel_name))
            shutil.copy(self.scratch.joinpath(f'tftpboot/live/{self.initrd_name}'), self.workspace.joinpath(self.initrd_name))
            shutil.copy(self.scratch.joinpath(f'binary/live/{self.squashfs_name}'), self.workspace.joinpath(self.squashfs_name))
            return True
        except Exception as ex:
            logging.error('Exception while collect_files: %s' % ex)
            return False

    def update_metadata(self):
        # modify metadata fields
        try:
            self.bootimage_metadata['release'] = self.task_payload['debian_release']
            self.bootimage_metadata['image_type'] = 'debian-liveimage'
            self.bootimage_metadata['arch'] = self.task_payload['arch']
            if self.task_payload['comment'] == '':
                self.bootimage_metadata['description'] = f'Auto-generated on {self.created}'
            else:
                self.bootimage_metadata['description'] = self.task_payload['comment']
            return True
        except Exception as ex:
            logging.error('Exception while update_metadata: %s' % ex)
            return False

    def generate_ipxe(self):
        # generate iPXE script
        # stage2.ipxe
        stage2ipxe = dedent('''\
        # created by NSTask_Image_DebianLive on %s
        # debian liveimage %s %s
        # %s
        set extra-kernel-args %s
        set kernel-name %s
        set initrd-name %s
        set squashfs-name %s
        set live-kernel-args initrd=${initrd-name} boot=live config hooks=filesystem username=live noeject fetch=${boot-image-path}/${squashfs-name}
        imgfree
        imgfetch ${boot-image-path}/${kernel-name} || goto failed
        imgfetch ${boot-image-path}/${initrd-name} || goto failed
        imgload ${kernel-name} || goto failed
        imgargs ${kernel-name} ${live-kernel-args} -- ${extra-kernel-args} || goto failed
        imgexec || goto failed
        ''' % (self.created, self.bootimage_metadata['release'], self.bootimage_metadata['arch'], self.bootimage_metadata['description'], self.task_payload['kernel_args'], self.kernel_name, self.initrd_name, self.squashfs_name))

        try:
            with open(self.workspace.joinpath('stage2.ipxe'), 'wt', encoding='utf-8') as f:
                f.write(stage2ipxe)
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
            'task_type': 'image_debian_liveimage',
            'task_payload': {
                'arch': 'amd64',
                'include_xfce': False,
                'packages': 'htop',
                'debian_release': 'bullseye',
                'name': 'Jacks debian liveimage test build',
                'mirror': 'http://deb.debian.org/debian',
                'kernel_args': 'ipv6.disable=1 IPV6_DISABLE=1 net.ifnames=0 biosdevname=0',
                'comment': 'Testing debian-liveimage',
            },
            'task_id': str(uuid.uuid4()),
            'task_name': 'New Debian Liveimage boot image',
            'task_description': 'Create a new Debian Liveimage boot image'
        }
        PATHS_TEST = build_paths('/opt/NetbootStudio')
        taskobj = NSTask_Image_DebianLive(PATHS_TEST, send_message, TEST_TASK)
        taskobj.start()

    except Exception as e:
        logging.exception('i had an exception')
