#!/usr/bin/env python3
"""
Netboot Studio File Manager
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2021 James Bishop (james@bishopdynamics.com)

import logging

from NSDataSource import NSDataSource


class NSFileManager(object):
    # provide an interface through which to get info about files
    list_names = [
        'ipxe_builds',
        'wimboot_builds',
        'stage1_files',
        'uboot_scripts',
        'boot_images',
        'unattended_configs',
        'iso',
        'tftp_root',
        'stage4',
    ]
    data_sources = {}

    def __init__(self, config, paths, loop):
        self.config = config
        self.paths = paths
        self.loop = loop
        for list_name in self.list_names:
            self.data_sources[list_name] = NSDataSource(self.config, self.paths, self.loop, list_name, 'consumer')
        logging.debug('FileManager is ready')

    def get_files(self, list_name):
        if list_name in self.data_sources:
            return self.data_sources[list_name].get_value()
        else:
            logging.warning('FileManager does not know list: %s' % list_name)
            return []
