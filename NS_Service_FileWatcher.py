#!/usr/bin/env python3
"""
Netboot Studio Service: API Server
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2023 James Bishop (james@bishopdynamics.com)

import sys
import json
import yaml
import pathlib
import logging
import argparse

from NSLogger import get_logger
from NSService import NSService
from NSDataSource import NSDataSource
from NSCommon import get_file_modified, validate_boot_image_metadata, sort_by_key


class NSFileWatcherService(NSService):
    """
    Netboot Studio File Watcher Service. Monitors the files we care about and publishes changes
    """
    mqtt_topics = [('api_request', 0), ]
    uploader = None

    def __init__(self, args):
        """
        File Watcher Service
        :param args: command-line arguments
        :type args: Namespace
        """
        super().__init__(args)
        logging.info('Netboot Studio File Watcher Server v%s', self.version)
        self.file_watcher = NSFileWatcher(self.config, self.paths, self.loop)
        logging.info('FileWatcher Server is ready')
        self.start()


class NSFileWatcher(object):
    # TODO use filesystem hooks to register changes
    scan_cycle = 1  # seconds, how often our data sources should update
    builtin_files = {
        'stage1_files': [
            {
                'filename': 'default',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: default Netboot Studio behavior (chain stage2.ipxe with a pile of paramters)',
            },
            {
                'filename': 'none',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: none (use as a shim on systems with missing or bad netbooting rom)',
            },
        ],
        'uboot_scripts': [
            {
                'filename': 'default',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: default Netboot Studio behavior (empty, does nothing)',
            },
        ],
        'unattended_configs': [
            {
                'filename': 'blank.cfg',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: an empty .cfg file',
            },
            {
                'filename': 'blank.xml',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: an empty .xml file',
            },
        ],
        'boot_images': [
            {
                'boot_image_name': 'standby_loop',
                'created': '1970-01-01_00:00:00',
                'image_type': 'builtin',
                'description': 'builtin: loop on 10s cycle, until a different boot image is selected',
                'arch': 'all',
            },
            {
                'boot_image_name': 'menu',
                'created': '1970-01-01_00:00:00',
                'image_type': 'builtin',
                'description': 'builtin: show an interactive menu listing all boot images',
                'arch': 'all',
            },
        ],
        'tftp_root': [
            {
                'filename': 'ipxe.bin',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: endpoint for ipxe build',
            },
            {
                'filename': 'boot.scr.uimg',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: endpoint for u-boot script',
            },
        ],
        # NOTE this differs from what is in messageprocessor because these actually show in the list
        'stage4': [
            {
                'filename': 'none',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: no script',
            },
        ],
    }
    data_sources = {}

    def __init__(self, config, paths, loop):
        self.config = config
        self.paths = paths
        self.loop = loop
        self.list_names = {
            'ipxe_builds': self.get_ipxe_builds,
            'wimboot_builds': self.get_wimboot_builds,
            'stage1_files': self.get_stage1_files,
            'uboot_scripts': self.get_uboot_scripts,
            'boot_images': self.get_boot_images,
            'unattended_configs': self.get_unattended_configs,
            'iso': self.get_iso,
            'tftp_root': self.get_tftp_root,
            'stage4': self.get_stage4,
        }
        logging.info('Starting FileWatcher')
        for list_name, get_function in self.list_names.items():
            self.data_sources[list_name] = NSDataSource(self.config, self.paths, self.loop, list_name, 'provider', get_function, self.scan_cycle)
        logging.debug('FileWatcher is ready')

    def get_stage1_files(self):
        stage1_folder = pathlib.Path(self.paths['stage1_files'])
        stage1_files = []
        # add builtins
        stage1_files += self.builtin_files['stage1_files']
        # find files in folder
        for this_file in stage1_folder.glob('*.[iI][pP][xX][eE]'):
            this_modified = get_file_modified(this_file)
            this_res = {'filename': str(this_file.name), 'modified': this_modified, 'description': ''}
            stage1_files.append(this_res)
        return sort_by_key(stage1_files, 'filename')

    def get_iso(self):
        iso_folder = pathlib.Path(self.paths['iso'])
        iso = []
        # find files in folder
        for this_file in iso_folder.glob('*.[iI][sS][oO]'):
            this_modified = get_file_modified(this_file)
            this_res = {'filename': str(this_file.name), 'modified': this_modified, 'description': ''}
            iso.append(this_res)
        return sort_by_key(iso, 'filename')

    def get_tftp_root(self):
        tftp_folder = pathlib.Path(self.paths['tftp_root'])
        tftp_root = []
        # add builtins
        tftp_root += self.builtin_files['tftp_root']
        # find files in folder
        # TODO this lists everything, but our system isnt really setup for file path navigation
        for this_file in tftp_folder.glob('*'):
            if str(this_file.name) == '.metadata' or str(this_file.name) == '.resources':
                continue  # ignore hidden folders used by uploader
            this_modified = get_file_modified(this_file)
            this_res = {'filename': str(this_file.name), 'modified': this_modified, 'description': ''}
            tftp_root.append(this_res)
        return sort_by_key(tftp_root, 'filename')

    def get_uboot_scripts(self):
        uboot_scripts_folder = pathlib.Path(self.paths['uboot_scripts'])
        uboot_scripts = []
        # add builtins
        uboot_scripts += self.builtin_files['uboot_scripts']
        # find files in folder
        for this_file in uboot_scripts_folder.glob('*.[sS][cC][rR]'):
            this_modified = get_file_modified(this_file)
            this_res = {'filename': str(this_file.name), 'modified': this_modified, 'description': ''}
            uboot_scripts.append(this_res)
        return sort_by_key(uboot_scripts, 'filename')

    def get_unattended_configs(self):
        uc_folder = pathlib.Path(self.paths['unattended_configs'])
        unattended_configs = []
        unattended_configs += self.builtin_files['unattended_configs']
        for this_file in uc_folder.glob('*.[cC][fF][gG]'):
            this_modified = get_file_modified(this_file)
            this_res = {'filename': str(this_file.name), 'modified': this_modified, 'description': ''}
            unattended_configs.append(this_res)
        for this_file in uc_folder.glob('*.[xX][mM][lL]'):
            this_modified = get_file_modified(this_file)
            this_res = {'filename': str(this_file.name), 'modified': this_modified, 'description': ''}
            unattended_configs.append(this_res)
        return sort_by_key(unattended_configs, 'filename')

    def get_stage4(self):
        stage4_folder = pathlib.Path(self.paths['stage4'])
        stage4 = []
        stage4_builtins = ['stage4-entry-unix.sh', 'stage4-entry-windows.bat', 'none']
        stage4 += self.builtin_files['stage4']
        for this_file in stage4_folder.glob('*.[sS][hH]'):
            this_modified = get_file_modified(this_file)
            if str(this_file.name) in stage4_builtins:
                logging.warning('a real file matching one of the builtin stage4 entrypoints exists! It will be ignored. file: %s' % this_file.name)
                continue  # skip anything that matches the builtins
            this_res = {'filename': str(this_file.name), 'modified': this_modified, 'description': ''}
            stage4.append(this_res)
        for this_file in stage4_folder.glob('*.[bB][aA][tT]'):
            this_modified = get_file_modified(this_file)
            if str(this_file.name) in stage4_builtins:
                logging.warning('a real file matching one of the builtin stage4 entrypoints exists! %s' % this_file.name)
                continue  # skip anything that matches the builtins
            this_res = {'filename': str(this_file.name), 'modified': this_modified, 'description': ''}
            stage4.append(this_res)
        return sort_by_key(stage4, 'filename')

    def get_boot_images(self):
        # parse metadata from all the available boot images
        boot_images = []
        # builtins first
        boot_images += self.builtin_files['boot_images']
        # a-la-carte images
        for this_file in pathlib.Path(self.paths['boot_images']).glob('*.[iI][pP][xX][eE]'):
            # TODO it makes more sense for files to have modified rather than created,
            #  but we cannot rename the key because the schema needs to match on both file and folder
            this_modified = get_file_modified(this_file)
            metadata = {
                'created': this_modified,
                'image_type': 'a-la-carte',
                'description': '%s, a file found in boot_images/' % this_file.name,
                'release': 'none',
                'arch': 'none',
                'boot_image_name': this_file.name,
                'stage2_filename': this_file.name,
                'supports_unattended': 'false',
                'stage2_unattended_filename': 'none',
            }
            if validate_boot_image_metadata(metadata):
                boot_images.append(metadata)
        # boot image folders
        for boot_image in pathlib.Path(self.paths['boot_images']).iterdir():
            if boot_image.is_dir():
                image_name = str(boot_image.name)
                metafile = boot_image.joinpath('metadata.yaml')
                if metafile.is_file():
                    try:
                        with open(metafile, 'r') as mf:
                            metadata = yaml.full_load(mf)
                    except KeyError:
                        logging.error('unable to parse build metadata file: %s' % metafile)
                        continue
                    metadata['boot_image_name'] = image_name
                    if validate_boot_image_metadata(metadata):
                        boot_images.append(metadata)
        return sort_by_key(boot_images, 'boot_image_name')

    def get_ipxe_builds(self):
        # parse metadata from all the available builds in ipxe_builds
        ipxe_builds = []
        for build in pathlib.Path(self.paths['ipxe_builds']).iterdir():
            if build.is_dir():
                metafile = build.joinpath('metadata.json')
                if metafile.is_file():
                    try:
                        with open(metafile, 'r') as mf:
                            metadata = json.load(mf)
                        build_id = metadata['build_id']
                        if build_id == '':
                            logging.error('woah, the build_id is empty')
                    except KeyError:
                        logging.error('unable to parse build metadata file: %s' % metafile)
                        continue
                    ipxe_builds.append(metadata)
        return sort_by_key(ipxe_builds, 'build_name')

    def get_wimboot_builds(self):
        # parse metadata from all the available builds in wimboot_builds
        wimboot_builds = []
        for build in pathlib.Path(self.paths['wimboot_builds']).iterdir():
            if build.is_dir():
                metafile = build.joinpath('metadata.json')
                if metafile.is_file():
                    try:
                        with open(metafile, 'r') as mf:
                            metadata = json.load(mf)
                        build_id = metadata['build_id']
                        if build_id == '':
                            logging.error('woah, the build_id is empty')
                    except KeyError:
                        logging.error('unable to parse build metadata file: %s' % metafile)
                        continue
                    wimboot_builds.append(metadata)
        return sort_by_key(wimboot_builds, 'build_name')


if __name__ == "__main__":
    # this is the main entry point
    ARG_PARSER = argparse.ArgumentParser(description='Netboot Studio API Server', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ARG_PARSER.add_argument('-m', dest='mode', action='store',
                            type=str, default='prod', choices=['prod', 'dev'],
                            help='which mode to run in')
    ARG_PARSER.add_argument('-c', dest='configdir', action='store',
                            type=str, default='/opt/NetbootStudio',
                            help='path to config folder')
    ARGS = ARG_PARSER.parse_args()
    if ARGS.mode == 'dev':
        # dev mode has info logging, but with lots of extra internal info at each log
        LOG_LEVEL = logging.DEBUG
    else:
        LOG_LEVEL = logging.INFO
    # courtesy of NSLogger
    logger = get_logger(name=__name__,
                        level=LOG_LEVEL)
    assert sys.version_info >= (3, 8), "Script requires Python 3.8+."
    NS = NSFileWatcherService(ARGS)
