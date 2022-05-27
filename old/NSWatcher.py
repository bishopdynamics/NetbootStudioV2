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

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler, FileCreatedEvent
from abc import abstractmethod

from NSCommon import get_file_modified, validate_boot_image_metadata, NSSafeQueue, async_process_queue_generic, print_object


class NSWatcher(object):
    # TODO our is_dir key is always going to be false if a folder was deleted
    # TODO prevent overwrite of builtins
    # TODO there is a utils.dirsnapshot method!!

    def __init__(self, config, paths, name, patterns, queue, ignore_patterns=None, ignore_directories=True, case_sensitive=False, recursive=False):
        self.config = config
        self.paths = paths
        self.name = name
        logging.debug('initializing NSWatcher for path: %s' % str(self.name))
        self.path = pathlib.Path(self.paths[self.name])
        self.patterns = patterns
        self.queue = queue
        if ignore_patterns is not None:
            self.ignore_patterns = ignore_patterns
        else:
            self.ignore_patterns = ['.DS_Store', '.git', '.gitignore']
        self.ignore_directories = ignore_directories
        self.case_sensitive = case_sensitive
        self.recursive = recursive
        logging.getLogger('fsevents').setLevel(logging.INFO)  # useful for debugging but also spammy
        self.log_events = False
        self.event_handler = PatternMatchingEventHandler(self.patterns, self.ignore_patterns, self.ignore_directories, self.case_sensitive)
        self.observer = Observer()
        self.observer.setDaemon(True)
        self.event_handler.on_created = self.on_created
        self.event_handler.on_deleted = self.on_deleted
        self.event_handler.on_modified = self.on_modified
        self.event_handler.on_moved = self.on_moved
        self.scheduled_watcher = self.observer.schedule(event_handler=self.event_handler, path=str(self.path), recursive=self.recursive)
        # self.set_initial_state()

    def set_initial_state(self):
        # get the current state by following each pattern and calling queuing events for each result
        #   TODO does creating event this way apply filtering?
        #   TODO this cant handle recursive
        logging.debug('setting initial state of %s' % self.name)
        for glob in self.patterns:
            for result in self.path.glob(glob):
                event = FileCreatedEvent(result)
                event.event_type = 'created'
                self.observer.event_queue.put((event, self.scheduled_watcher))

    def start(self):
        logging.debug('starting NSWatcher for path: %s' % str(self.path))
        self.observer.start()

    def filter_items(self, item):
        # by default does nothing, just returns the item. override this to make more decisions
        return item

    def on_created(self, event):
        if self.log_events:
            print_object('watchdog c_event', event)
        item = {
            'name': self.name,
            'path': self.path,
            'event': 'created',
            'eventpath': pathlib.Path(event.src_path),
            'eventname': str(pathlib.Path(event.src_path)).split('/')[-1],
            'is_pdir': pathlib.Path(event.src_path).is_dir(),  # is this eventpath a dir according to pathlib?
            'is_dir': event.is_directory,  # is this eventpath a dir according to watchdog?
            'is_synth': event.is_synthetic,  # synthetic events did not originate from os events, were implied by other real events
        }
        filtered_item = self.filter_items(item)
        if filtered_item is not None:
            self.queue.put(filtered_item)

    def on_deleted(self, event):
        if self.log_events:
            print_object('watchdog d_event', event)
        item = {
            'name': self.name,
            'path': self.path,
            'event': 'deleted',
            'eventpath': pathlib.Path(event.src_path),
            'eventname': str(pathlib.Path(event.src_path)).split('/')[-1],
            'is_pdir': pathlib.Path(event.src_path).is_dir(),
            'is_dir': event.is_directory,
            'is_synth': event.is_synthetic,
        }
        filtered_item = self.filter_items(item)
        if filtered_item is not None:
            self.queue.put(filtered_item)

    def on_modified(self, event):
        if self.log_events:
            print_object('watchdog m_event', event)
        item = {
            'name': self.name,
            'path': self.path,
            'event': 'modified',
            'eventpath': pathlib.Path(event.src_path),
            'eventname': str(pathlib.Path(event.src_path)).split('/')[-1],
            'is_pdir': pathlib.Path(event.src_path).is_dir(),
            'is_dir': event.is_directory,
            'is_synth': event.is_synthetic,
        }
        filtered_item = self.filter_items(item)
        if filtered_item is not None:
            self.queue.put(filtered_item)

    def on_moved(self, event):
        if self.log_events:
            print_object('watchdog mv_event', event)
        item = {
            'name': self.name,
            'path': self.path,
            'event': 'moved',
            'eventpath': pathlib.Path(event.src_path),
            'eventname': str(pathlib.Path(event.src_path)).split('/')[-1],
            'is_dir': event.is_directory,
            'is_pdir': pathlib.Path(event.dest_path).is_dir(),
            'is_synth': event.is_synthetic,
            'topath': pathlib.Path(event.dest_path),
            'toname': str(pathlib.Path(event.dest_path)).split('/')[-1],
        }
        filtered_item = self.filter_items(item)
        if filtered_item is not None:
            self.queue.put(filtered_item)


class NSWatcher_boot_images(NSWatcher):

    def __init__(self, config, paths, queue):
        super().__init__(config, paths, name='boot_images', patterns=['*'], queue=queue, ignore_patterns=None, ignore_directories=True, case_sensitive=False, recursive=False)

    def filter_item(self, item):
        # only return items that match our criteria, and add some extra data to help
        #  we can have a-la-carte boot images (something.ipxe) or folder boot image (something/metadata.yaml)
        if item['event'] in ['created', 'modified', 'deleted']:
            if item['eventname'] == 'metadata.yaml':
                # creating or changing a folder boot image
                item['boot_image_type'] = 'folder'
                if item['eventpath'].parents[1] == self.paths[self.name]:
                    # this file was found in a subfolder of boot_images
                    item['boot_image_name'] = item['eventpath'].parents[0].name
                    if item['event'] == 'created':
                        # created a boot image of folder type
                        item['ns_event'] = 'created'
                        return item
                    if item['event'] == 'modified':
                        # modified metatada of a folder boot image
                        item['ns_event'] = 'modified'
                        return item
                    if item['event'] == 'deleted':
                        # the metadata deleted so the boot image is no longer valid, remove it
                        item['ns_event'] = 'deleted'
                        return item
            else:
                # not metadata.yaml
                if '.ipxe' in item['eventname']:
                    # a-la-carte file boot image
                    item['boot_image_type'] = 'a-la-carte'
                    if not item['eventpath'].is_dir():
                        # and its not a folder with .ipxe in the name
                        if str(item['eventpath'].parents[0]) == str(self.paths[self.name]):
                            # this file was found in boot_images top level
                            item['boot_image_name'] = item['eventname']
                            if item['event'] == 'created':
                                # created a boot image of folder type
                                item['ns_event'] = 'created'
                                return item
                            if item['event'] == 'modified':
                                # modified metatada of a folder boot image
                                item['ns_event'] = 'modified'
                                return item
                            if item['event'] == 'deleted':
                                # the metadata deleted so the boot image is no longer valid, remove it
                                item['ns_event'] = 'deleted'
                                return item
        if item['event'] == 'moved':
            if item['eventpath'].parents[0] == self.paths[self.name] and item['topath'].parents[0] == self.paths[self.name]:
                # moved to and from both in our folder
                item['ns_event'] = 'renamed'
                return item
            elif item['topath'].parents[0] == self.paths[self.name]:
                # moved into our folder, new item
                item['ns_event'] = 'created'
                return item
            elif item['eventpath'].parents[0] == self.paths[self.name]:
                # moved away, delete
                item['ns_event'] = 'deleted'
                return item
        return None

    def create_queue_object(self, item):
        # parse metadata from all the available boot images
        #   return a queue object with action: add_item, update_item, remove_item, move_item
        #   this methods job is to do all the work of reading files and parsing data
        #  we can have a-la-carte boot images (something.ipxe) or folder boot image (something/metadata.yaml)
        print_object('NSWatcher item:', item)
        # created, modified, deleted, renamed
        event_type = item['ns_event']
        is_pdir = item['is_pdir']
        boot_image_type = item['boot_image_type']
        boot_image_name = item['boot_image_name']
        boot_image_folder = self.paths['boot_images'].joinpath(boot_image_name)
        metafile = boot_image_folder.joinpath('metadata.yaml')
        queue_object = {
            'action': None,
            'cache_name': 'boot_images',
            'name': boot_image_name,
            'metadata': None
        }
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
                    queue_object['metadata'] = metadata
                    if event_type == 'created':
                        queue_object['action'] = 'add_item'
                    elif event_type == 'modified':
                        queue_object['action'] = 'update_item'
                    return queue_object
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
                    queue_object['metadata'] = metadata
                    if item['event'] == 'created':
                        queue_object['action'] = 'add_item'
                    elif item['event'] == 'modified':
                        queue_object['action'] = 'update_item'
                    return queue_object
        elif item['event'] == 'deleted':
            queue_object['action'] = 'remove_item'
            return queue_object
        elif item['event'] == 'moved':
            queue_object['from_name'] = item['']
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
                queue_object['metadata'] = metadata
                if not is_pdir:
                    queue_object['allowed_extensions'] = ['.ipxe']
                queue_object['action'] = 'move_item'
                return queue_object
        return None
