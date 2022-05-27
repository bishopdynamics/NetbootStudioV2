#!/usr/bin/env python3
"""
Netboot Studio File Manager
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2021 James Bishop (james@bishopdynamics.com)

import pathlib
import logging
import yaml
import json

from NSWatcher import NSWatcher, NSWatcher_boot_images

from NSCommon import get_file_modified, validate_boot_image_metadata, NSSafeQueue, async_process_queue_generic, print_object


class NSFileManager(object):
    # TODO every N hours, builds list of ipxe commit ids
    # TODO Start Over
    scan_cycle = 10  # seconds, how often to scan
    # we preseed the cache with builtins
    cache = {
        'ipxe_builds': [],
        'wimboot_builds': [],
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
        'boot_images': [
            {
                'name': 'standby_loop',
                'created': '1970-01-01_00:00:00',
                'image_type': 'builtin',
                'description': 'builtin: loop on 10s cycle, until a different boot image is selected',
                'arch': 'all',
            },
            {
                'name': 'menu',
                'created': '1970-01-01_00:00:00',
                'image_type': 'builtin',
                'description': 'builtin: show an interactive menu listing all boot images',
                'arch': 'all',
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
        'iso': [],
        'tftp_root': [
            {
                'filename': 'ipxe.efi',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: endpoint for ipxe build',
            },
            {
                'filename': 'boot.scr.uimg',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: endpoint for u-boot script',
            },
        ],
    }
    watchers = {}

    def __init__(self, config, paths, mqtt_client, loop):
        self.config = config
        self.paths = paths
        self.mqtt_client = mqtt_client
        self.loop = loop
        self.queue = NSSafeQueue(self.loop)
        self.change_handlers = {
            'stage1_files': self.handle_event_stage1_files,
            'iso': self.handle_event_iso,
            'tftp_root': self.handle_event_tftp_root,
            'uboot_scripts': self.handle_event_uboot_scripts,
            'unattended_configs': self.handle_event_unattended_configs,
            'boot_images': self.handle_event_boot_images,
            'ipxe_builds': self.handle_event_ipxe_builds,
            'wimboot_builds': self.handle_event_wimboot_builds,
        }
        logging.info('Starting FileManager')
        self.process_queue_task = self.loop.create_task(self.process_queue())
        self.start()
        logging.debug('FileManager is ready')

    def start(self):
        # self.watchers['stage1_files'] = NSWatcher(self.config, self.paths, 'stage1_files', ['*.ipxe'], self.queue)
        # self.watchers['iso'] = NSWatcher(self.config, self.paths, 'iso', ['*.iso'], self.queue)
        # # TODO tftp root should actually be done recursive and we should build a nice big tree forit. right now its just listing files in top level of tftp_root
        # self.watchers['tftp_root'] = NSWatcher(self.config, self.paths, 'tftp_root', ['*.*'], self.queue)
        # self.watchers['uboot_scripts'] = NSWatcher(self.config, self.paths, 'uboot_scripts', ['*.scr'], self.queue)
        # self.watchers['unattended_configs'] = NSWatcher(self.config, self.paths, 'unattended_configs', ['*.cfg', '*.xml'], self.queue)
        self.watchers['boot_images'] = NSWatcher_boot_images(self.config, self.paths, self.queue)
        # self.watchers['ipxe_builds'] = NSWatcher(self.config, self.paths, 'ipxe_builds', ['*'], self.queue, ignore_directories=False, recursive=True)
        # self.watchers['wimboot_builds'] = NSWatcher(self.config, self.paths, 'wimboot_builds', ['*'], self.queue, ignore_directories=False, recursive=True)
        for name, entry in self.watchers.items():
            logging.debug('starting watcher named: %s' % name)
            entry.start()

    def stop(self):
        logging.info('Shutting down File Manager')
        self.process_queue_task.cancel()

    def get_files(self, cachename):
        return self.cache[cachename]

    def handle_change_from_queue(self, item):
        # logging.debug('handling change %s from: %s' % (item['event'], item['name']))
        # print_object('NSWatcher item:', item)
        # return
        # if item['name'] in self.change_handlers:
        #     self.change_handlers[item['name']](item)
        if item['action'] == 'move_item':
            self.move_item(item['cache_name'], item['from_name'], item['to_name'], matchkey=item['matchkey'], metadata=item['metadata'], allowed_extensions=item['allowed_extensions'])
        elif item['action'] == 'remove_item':
            self.remove_item(item['cache_name'], matchvalue=item['name'], matchkey='name')
        elif item['action'] == 'update_item':
            self.update_item(item['cache_name'], matchvalue=item['name'], matchkey='name', metadata=item['metadata'])
        elif item['action'] == 'add_item':
            self.add_item(item['cache_name'], item['name'], metadata=item['metadata'])

    async def process_queue(self):
        await async_process_queue_generic(self.queue, self.handle_change_from_queue, 0.2)

    def handle_files_generic(self, this_name, item, allowed_extensions=None):
        # allowed_extensions is only used to validate when a file is moved to a new extension
        if item['eventpath'].is_file():
            if item['event'] == 'created' or item['event'] == 'modified':
                metadata = {
                    'filename': item['eventname'],
                    'modified': get_file_modified(item['eventpath']),
                    'description': 'found in %s/' % this_name
                }
                if item['event'] == 'created':
                    self.add_item(this_name, item['eventname'], metadata=metadata)
                if item['event'] == 'modified':
                    self.update_item(this_name, matchvalue=item['eventname'], matchkey='filename', metadata=metadata)
        else:
            if item['event'] == 'deleted':
                self.remove_item(this_name, matchvalue=item['eventname'], matchkey='filename')
            if item['event'] == 'moved':
                metadata = {
                    'filename': item['toname'],
                    'modified': get_file_modified(item['topath']),
                    'description': 'found in %s/' % this_name
                }
                self.move_item(this_name, item['eventname'], item['toname'], 'filename', metadata, allowed_extensions=allowed_extensions)

    def move_item(self, this_name, fromname, toname, matchkey, metadata, allowed_extensions=None):
        logging.debug('moving an item in %s, from %s, to %s' % (this_name, fromname, toname))
        self.remove_item(this_name, matchvalue=fromname, matchkey=matchkey)
        # if we renamed it to an extension we dont allow, there is no need to add item
        if allowed_extensions is None:
            self.add_item(this_name, toname, metadata=metadata)
        else:
            for extension in allowed_extensions:
                if extension in toname:
                    self.add_item(this_name, toname, metadata=metadata)
                    break  # just in case its named something.cfg.xml, first match wins, dont add it twice

    def remove_item(self, this_name, matchvalue, matchkey):
        logging.debug('removing an item from %s, named: %s' % (this_name, matchvalue))
        for entry in self.cache[this_name]:
            if entry[matchkey] == matchvalue:
                self.cache[this_name].remove(entry)

    def update_item(self, this_name, matchvalue, matchkey, metadata):
        # note this assumes static schema for metadata, and thus a key will not be added or removed, only updated
        logging.debug('updating an item in %s, named: %s' % (this_name, matchvalue))
        for entry in self.cache[this_name]:
            if entry[matchkey] == matchvalue:
                for keyname, value in metadata.items():
                    entry[keyname] = value
                break

    def add_item(self, this_name, item_name, metadata):
        logging.debug('adding an item to %s, named: %s' % (this_name, item_name))
        self.cache[this_name].append(metadata)

    def handle_event_stage1_files(self, item):
        self.handle_files_generic('stage1_files', item, ['.ipxe'])

    def handle_event_iso(self, item):
        self.handle_files_generic('iso', item, ['.iso'])

    def handle_event_tftp_root(self, item):
        self.handle_files_generic('tftp_root', item)

    def handle_event_uboot_scripts(self, item):
        self.handle_files_generic('uboot_scripts', item, ['.scr'])

    def handle_event_unattended_configs(self, item):
        self.handle_files_generic('unattended_configs', item, ['.cfg', '.xml'])

    def handle_event_boot_images(self, item):
        # parse metadata from all the available boot images
        #  we can have a-la-carte boot images (something.ipxe) or folder boot image (something/metadata.yaml)
        print_object('NSWatcher item:', item)
        # created, modified, deleted, renamed
        this_name = 'boot_images'
        event_type = item['ns_event']
        is_pdir = item['is_pdir']
        boot_image_type = item['boot_image_type']
        boot_image_name = item['boot_image_name']
        boot_image_folder = self.paths['boot_images'].joinpath(boot_image_name)
        metafile = boot_image_folder.joinpath('metadata.yaml')
        if event_type in ['created', 'modified']:
            if boot_image_type == 'a-la-carte':
                # a-la-carte file boot image
                try:
                    metadata = {
                        'created': get_file_modified(item['eventpath']),
                        'image_type': boot_image_type,
                        'description': '%s, a file found in boot_images/' % boot_image_name,
                        'release': 'none',
                        'arch': 'none',
                        'name': boot_image_name,
                        'stage2_filename': boot_image_name,
                        'supports_unattended': 'false',
                        'stage2_unattended_filename': 'none',
                    }
                    if not validate_boot_image_metadata(metadata):
                        raise Exception('a-la-carte boot image metadata validation failed')
                except Exception as ex:
                    logging.error('unabe to parse boot image metadata for: %s, %s' % (boot_image_name, ex))
                else:
                    if event_type == 'created':
                        self.add_item(this_name, boot_image_name, metadata)
                    if event_type == 'modified':
                        self.update_item(this_name, matchvalue=boot_image_name, matchkey='name', metadata=metadata)
            elif boot_image_type == 'folder':
                # folder boot image
                try:
                    with open(metafile, 'r') as mf:
                        metadata = yaml.full_load(mf)
                    metadata['name'] = boot_image_name
                    if not validate_boot_image_metadata(metadata):
                        raise Exception('folder boot image metadata validation failed')
                except Exception as ex:
                    logging.error('unable to parse boot image metadata file: %s, ex: %s' % (metafile, ex))
                else:
                    if item['event'] == 'created':
                        self.add_item(this_name, boot_image_name, metadata)
                    if item['event'] == 'modified':
                        self.update_item(this_name, matchvalue=boot_image_name, matchkey='name', metadata=metadata)
        elif item['event'] == 'deleted':
            self.remove_item(this_name, matchvalue=boot_image_name, matchkey='name')
        elif item['event'] == 'moved':
            try:
                if boot_image_type == 'a-la-carte':
                    metadata = {
                        'created': get_file_modified(item['topath']),
                        'image_type': 'a-la-carte',
                        'description': '%s, a file found in boot_images/' % item['toname'],
                        'release': 'none',
                        'arch': 'none',
                        'name': item['toname'],
                        'stage2_filename': item['toname'],
                        'supports_unattended': 'false',
                        'stage2_unattended_filename': 'none',
                    }
                elif boot_image_type == 'folder':
                    with open(metafile, 'r') as mf:
                        metadata = yaml.full_load(mf)
                    metadata['name'] = boot_image_name
                if not validate_boot_image_metadata(metadata):
                    raise Exception('folder boot image metadata validation failed')
            except Exception as ex:
                logging.error('unable to parse boot image metadata: %s' % ex)
            else:
                if not item['is_dir']:
                    self.move_item(this_name, item['eventname'], item['toname'], 'name', metadata, allowed_extensions=['.ipxe'])
                else:
                    self.move_item(this_name, item['eventname'], item['toname'], 'name', metadata)

    def handle_event_ipxe_builds(self, item):
        # parse metadata from all the available builds in ipxe_builds
        #  TODO because this is not recursive we dont actually get modified events
        this_name = 'ipxe_builds'
        if item['event'] in ['created', 'modified']:
            if item['is_dir']:
                metafile = item['eventpath'].joinpath('metadata.json')
                try:
                    with open(metafile, 'r') as mf:
                        metadata = json.load(mf)
                    # TODO this should use a validate function like boot_images
                    build_id = metadata['build_id']
                except Exception as ex:
                    logging.error('unable to parse build ipxe metadata file: %s, ex: %s' % (metafile, ex))
                else:
                    if item['event'] == 'created':
                        self.add_item(this_name, item_name=item['eventname'], metadata=metadata)
                    if item['event'] == 'modified':
                        self.update_item(this_name, matchvalue=item['eventname'], matchkey='build_id', metadata=metadata)
        elif item['event'] == 'deleted':
            self.remove_item(this_name, matchvalue=item['eventname'], matchkey='name')
        elif item['event'] == 'moved':
            metafile = item['topath'].joinpath('metadata.json')
            try:
                with open(metafile, 'r') as mf:
                    metadata = json.load(mf)
                # TODO this should use a validate function like boot_images
                build_id = metadata['build_id']
            except Exception as ex:
                logging.error('unable to parse ipxe build metadata file: %s, ex: %s' % (metafile, ex))
            else:
                self.move_item(this_name, item['eventname'], item['toname'], 'name', metadata)

    def handle_event_wimboot_builds(self, item):
        # parse metadata from all the available builds in wimboot_builds
        #  TODO because this is not recursive we dont actually get modified events
        this_name = 'wimboot_builds'
        if item['event'] in ['created', 'modified']:
            metafile = item['eventpath'].joinpath('metadata.json')
            try:
                with open(metafile, 'r') as mf:
                    metadata = json.load(mf)
                # TODO this should use a validate function like boot_images
                build_id = metadata['build_id']
            except Exception as ex:
                logging.error('unable to parse wimboot build metadata file: %s, ex: %s' % (metafile, ex))
            else:
                if item['event'] == 'created':
                    self.add_item(this_name, item_name=item['eventname'], metadata=metadata)
                if item['event'] == 'modified':
                    self.update_item(this_name, matchvalue=item['eventname'], matchkey='build_id', metadata=metadata)
        elif item['event'] == 'deleted':
            self.remove_item(this_name, matchvalue=item['eventname'], matchkey='build_id')
        elif item['event'] == 'moved':
            metafile = item['topath'].joinpath('metadata.json')
            try:
                with open(metafile, 'r') as mf:
                    metadata = json.load(mf)
                # TODO this should use a validate function like boot_images
                build_id = metadata['build_id']
            except Exception as ex:
                logging.error('unable to parse wimboot build metadata file: %s, ex: %s' % (metafile, ex))
            else:
                self.move_item(this_name, item['eventname'], item['toname'], 'name', metadata)

