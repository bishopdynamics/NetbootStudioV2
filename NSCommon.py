#!/usr/bin/env python3
"""
Netboot Studio Common Functions
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2023 James Bishop (james@bishopdynamics.com)

# ignore rules:
#   docstring
#   too-broad-exception
#   line-too-long
#   too-many-branches
#   too-many-statements
#   too-many-public-methods
#   too-many-lines
#   too-many-nested-blocks
#   toddos (annotations linter handling this)
# pylint: disable=C0111,W0703,C0301,R0912,R0915,R0904,C0302,R1702,W0511

import sys
import os
import time
import logging
import pathlib
import json
import uuid
import datetime
import asyncio

from operator import itemgetter
from threading import Thread
from threading import active_count as threading_active_count
from pathvalidate import sanitize_filename, replace_symbol

import NSJanus

# this is the format we use for all timestamps, its in utc/zulu
NS_TIMESAMP_FORMAT = "%Y-%m-%d %H:%M:%S %z"


def sanitize_string(mystring):
    # sanitize a string suitable for use as a file name
    # https://pathvalidate.readthedocs.io/en/latest/pages/examples/sanitize.html
    return replace_symbol(sanitize_filename(str(mystring).replace(' ', '_')), exclude_symbols=['_', '-', '.'])

# give me a list of objects like [{},{},{}] and a keyname get a sorted list back
def sort_by_key(unsorted_list, keyname):
    sorted_list = sorted(unsorted_list, key=lambda obj: obj[keyname].lower(), reverse=False)
    return sorted_list


def print_object(prefix, item):
    # try to print this item as json string, casting to strings along the way if needed
    # its ugly, but can be helpful for troubleshooting
    newdict = {}
    try:
        if isinstance(item, tuple):
            logging.debug('%s%s' % (prefix, json.dumps(item, indent=4)))
        elif isinstance(item, list):
            logging.debug(prefix)
            logging.debug(item)
        else:
            if isinstance(item, dict):
                itemdict = item
            else:
                itemdict = item.__dict__
            for key, value in itemdict.items():
                try:
                    if isinstance(value, bool):
                        newdict[key] = 'bool(%s)' % value
                    elif isinstance(value, str):
                        newdict[key] = 'str(%s)' % value
                    elif isinstance(value, pathlib.Path):
                        newdict[key] = 'pathlib.Path(%s)' % str(value)
                    elif isinstance(value, dict):
                        newdict[key] = 'dict(%s)' % json.dumps(value)
                    else:
                        newdict[key] = 'unknown(%s)' % json.dumps(value)
                except Exception:
                    valuetype = type(value)
                    newdict[key] = 'failed to stringify key: %s, type: %s' % (key, valuetype)
            logging.debug('%s%s' % (prefix, json.dumps(newdict, indent=4)))
    except Exception as ex:
        logging.warning('Failed to print an object:', ex)


# validate all the required keys are present in boot image metadata
def validate_boot_image_metadata(metadata):
    # TODO you can validate even more
    #   check for existing files
    #   check key types, check that created is a valid timestamp
    #   check that name has only safe characters
    needed_keys = ['created', 'image_type', 'description', 'release', 'arch', 'boot_image_name', 'stage2_filename', 'supports_unattended']
    all_good = True
    for keyname in needed_keys:
        if keyname not in metadata:
            logging.error('boot image metadata missing key: %s' % keyname)
            all_good = False
        if keyname == 'supports_unattended':
            # turn supports_unattended into a real bool
            if str(metadata['supports_unattended']).lower() == 'true':
                metadata['supports_unattended'] = True
            else:
                metadata['supports_unattended'] = False
    if metadata['supports_unattended']:
        if 'stage2_unattended_filename' not in metadata:
            logging.error('boot image metadata missing key: stage2_unattended_filename')
            all_good = False

    return all_good


# standardize format for file modified timestamps
def get_file_modified(this_file):
    this_statbuf = os.stat(this_file)
    this_modified_dto = datetime.datetime.fromtimestamp(float(this_statbuf.st_mtime))
    this_modified = str(this_modified_dto.strftime(NS_TIMESAMP_FORMAT))
    return this_modified


def process_queue_generic(_queue, _item_handler):
    # just run through a queue with no restrictions til it is empty
    while True:
        while not _queue.empty():
            try:
                _item = _queue.get()
                _item_handler(_item)
            except Exception as ex:
                logging.error('Error while processing a queue: %s', ex)
            time.sleep(0.01)


async def async_process_queue_generic(_queue, _item_handler, cycle_time=0.01):
    # just run through a queue with no restrictions til it is empty, asyncio version
    while True:
        while not _queue.empty():
            try:
                _item = _queue.get()
                _item_handler(_item)
            except Exception as ex:
                logging.error('Error while processing a queue: %s', ex)
            await asyncio.sleep(cycle_time)
        await asyncio.sleep(cycle_time)


def get_version(path_base):
    # NOTE that when the docker image is built, VERSION is modified to include commit id
    with open(path_base.joinpath('VERSION'), 'r') as file:
        _version = file.read().replace('\n', '')
    return _version


# prepare string for the copyright line with version in it at bottom of the page
def get_copyright():
    version = get_version(get_program_dir())
    copyright_text = 'Copyright James Bishop (james@bishopdynamics.com) 2019-2023'
    full_string = '%s    %s' % (copyright_text, version)
    return full_string


def get_program_dir():
    # get the directory that will have our program resources
    # depending on exactly how NetbootStudio is executed, this may be different
    if '__compiled__' in globals():
        logging.debug('This is a binary package compiled using Nuitka')
        if pathlib.Path(os.path.realpath('/proc/self/exe')).is_file():
            # only linux does /proc/self/exe
            path_base = pathlib.Path(os.path.realpath('/proc/self/exe')).parent.absolute()
        else:
            # probably macos
            path_base = pathlib.Path(__file__).parent.absolute()
    else:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # getattr takes an argument to return if the attribute does not exist
        mei_base = getattr(sys, '_MEIPASS', False)
        if mei_base and pathlib.Path(mei_base).is_dir():
            logging.debug('This binary package appears to have been prepared using pyinstaller or similar')
            path_base = pathlib.Path(mei_base)
        else:
            logging.debug('This package is being run from native python source')
            path_base = pathlib.Path(__file__).parent.absolute()

    logging.debug('resources will be loaded from path_base: %s', path_base)
    return path_base


def start_workers_generic(num_threads, thread_prefix, thread_target):
    logging.debug('Starting worker threads')
    for i in range(num_threads):
        threadnum = threading_active_count() + 1
        threadname = '%s-%i' % (thread_prefix, (i + 1))
        logging.debug('Starting Thread-%i (%s)', threadnum, threadname)
        worker = Thread(target=thread_target)
        worker.setDaemon(True)
        worker.start()


def seconds_to_uptime_string(seconds, granularity=3):
    intervals = (
        ('w', 604800),  # 60 * 60 * 24 * 7
        ('d', 86400),    # 60 * 60 * 24
        ('h', 3600),    # 60 * 60
        ('m', 60),
        ('s', 1),
        )
    result = []
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            result.append("{}{}".format(value, name))
    return ', '.join(result[:granularity])


# builds our paths object that everything will use to find folders and files
def build_paths(config_dir):
    paths_object = dict()
    paths_object['config_base'] = pathlib.Path(config_dir)  # all user-provided config lives here
    paths_object['program_base'] = get_program_dir()
    paths_object['config.ini'] = paths_object['config_base'].joinpath('config.ini')  # operating variables live here, read only
    paths_object['settings.json'] = paths_object['config_base'].joinpath('settings.json')  # global application settings live here, read & write
    paths_object['certs'] = paths_object['config_base'].joinpath('certs')  # certs folder
    paths_object['ssl_ca_cert'] = paths_object['certs'].joinpath('ca_cert.pem')  # the root ca certificate used to sign the server certificate needed to embed in ipxe binaries
    paths_object['ssl_full_chain'] = paths_object['certs'].joinpath('full_chain.pem')  # full chain is needed for ipxe binaries
    paths_object['ssl_cert'] = paths_object['certs'].joinpath('server_cert.pem')  # SSL cert required for HTTPS and WSS
    paths_object['ssl_key'] = paths_object['certs'].joinpath('server_key.key')  # SSL key required for HTTPS and WSS
    paths_object['boot_images'] = paths_object['config_base'].joinpath('boot_images')  # boot_images folder
    paths_object['unattended_configs'] = paths_object['config_base'].joinpath('unattended_configs')  # unattended_configs folder
    paths_object['ipxe_builds'] = paths_object['config_base'].joinpath('ipxe_builds')  # where ipxe builds will live
    paths_object['wimboot_builds'] = paths_object['config_base'].joinpath('wimboot_builds')  # where wimboot builds will live
    paths_object['stage1_files'] = paths_object['config_base'].joinpath('stage1_files')  # where ipxe stage1 files live
    paths_object['web'] = paths_object['program_base'].joinpath('web')  # web resources live here
    paths_object['web_lib'] = paths_object['web'].joinpath('lib')  # web libraries live here js and css files
    paths_object['stage4'] = paths_object['config_base'].joinpath('stage4')  # stage4 config system lives here
    paths_object['stage4-entry-unix'] = paths_object['program_base'].joinpath('stage4-entry-unix.sh')  # the bulk of the stage4 entry file for unix-style systems
    paths_object['stage4-entry-windows'] = paths_object['program_base'].joinpath('stage4-entry-windows.bat')  # the bulk of the stage4 entry file for windows systems
    paths_object['packages'] = paths_object['config_base'].joinpath('packages')  # stage4 packages live here
    paths_object['tftp_root'] = paths_object['config_base'].joinpath('tftp_root')  # this is where normal tftp files will live
    paths_object['iso'] = paths_object['config_base'].joinpath('iso')  # uploaded iso files live here
    paths_object['uboot_scripts'] = paths_object['config_base'].joinpath('uboot_scripts')  # uboot scripts that become uboot binaries
    paths_object['uboot_binaries'] = paths_object['config_base'].joinpath('uboot_binaries')  # uboot binaries, aka boot.scr.uimg
    paths_object['temp'] = paths_object['config_base'].joinpath('temp')  # temporary scratch space for tasks
    path_strings = {}
    for entryname, pathobj in paths_object.items():
        path_strings[entryname] = str(pathobj)
    logging.debug(json.dumps(path_strings, indent=4))
    return paths_object


# check that all the folders and files we need exist already, try to make them if we can
def check_config(paths_obj):
    all_good = True
    folders_to_create = [
        'certs', 'boot_images', 'unattended_configs', 'ipxe_builds', 'wimboot_builds', 'stage1_files', 'stage4', 'packages', 'tftp_root', 'iso'
    ]
    if not paths_obj['config_base'].is_dir():
        logging.error('missing config dir: %s', paths_obj['config_base'])
        logging.error('  please create %s and make sure the approprate user(s) have appropriate permissions',  paths_obj['config_base'])
        all_good = False
    if not paths_obj['config.ini'].is_file():
        logging.error('missing config file: %s',  paths_obj['config.ini'])
        all_good = False
    if not paths_obj['ssl_cert'].is_file() or not paths_obj['ssl_key'].is_file() or not paths_obj['ssl_ca_cert'].is_file() or not paths_obj['ssl_full_chain'].is_file():
        logging.error('missing SSL certificates and/or keys which should be in: %s',  paths_obj['certs'])
        logging.error('  they should be named: server_cert.pem, server_key.key, ca_cert.pem, full_chain.pem')
        logging.error('  for testing, you can run ./generate-ssl-certs.sh to create a ca, and use it to create and sign cert and key in ./certs/')
        logging.error('  for production use, you must provide proper certificate')
        all_good = False
    if not all_good:
        logging.critical('failed preflight checks, see errors above')
        sys.exit(1)
    try:
        for foldername in folders_to_create:
            if not pathlib.Path(paths_obj[foldername]).is_dir():
                logging.info('creating missing folder: %s' % paths_obj[foldername])
                os.makedirs(paths_obj[foldername])
        logging.debug('check_config complete')
    except Exception:
        logging.exception('Unexpected exception while making folders')
        sys.exit(1)


# standard timestamp string format, optionally N minutes in the future, and optionally setting "now" to be from a string
def get_timestamp(plus_seconds=0, now_string=None):
    if now_string is not None:
        now_dto = datetime.datetime.strptime(now_string, NS_TIMESAMP_FORMAT)
    else:
        now_dto = datetime.datetime.now().astimezone()
    then_dto = now_dto + datetime.timedelta(seconds=plus_seconds)
    then_str = then_dto.strftime(NS_TIMESAMP_FORMAT)
    return str(then_str)


# return int seconds until the given string timestamp, 0 if it has passed
def get_seconds_until_timestamp(timestamp_string):
    then_dto = datetime.datetime.strptime(timestamp_string, NS_TIMESAMP_FORMAT)
    now_dto = datetime.datetime.now().astimezone()
    if then_dto > now_dto:
        # then is in the future
        time_delta = then_dto - now_dto
        seconds = time_delta.total_seconds()
    else:
        # then is not in the future
        seconds = 0
    return seconds


class NSSafeQueue(NSJanus.Queue):
    # threadsafe, asyncio safe, Queue with standard methods added back
    # note that we build upon a modified janus library

    def empty(self):
        return self._qsize() < 1

    def put(self, item):
        self._put(item)

    def get(self):
        return self._get()

    def length(self):
        return self._qsize()


class NSMessage:
    # common message format for http, websocket, and mqtt messages
    # if this came from the broker via a topic, that gets set within the message, otherwise it is blank and you must set it yourself
    _data = None

    def __init__(self, _msg=None):
        if _msg is not None:
            self.from_json(_msg)
        else:
            self._data = {
                'id': str(uuid.uuid4()),
                'sender': 'Unknown',
                'origin': None,
                'target': 'all',
                'topic': None,
                'content': dict(),
            }

    def to_json(self):
        try:
            _string = json.dumps(self._data)
        except Exception as ex:
            logging.error('Exception while dumping NSMessage to json: %s', ex)
            _string = ''
        return _string

    def from_json(self, _json):
        try:
            _parsed = json.loads(_json)
        except Exception as ex:
            logging.error('Exception while parsing NSMessage from json: %s', ex)
            _parsed = dict()
        self._data = _parsed

    def set(self, key, value):
        # TODO rename this to set_key (in javascript, cant name method set)
        if key == 'id':
            logging.error('Cannot change the id of a message!')
        else:
            try:
                self._data[key] = value
            except Exception as ex:
                logging.error('Exception while setting key: %s, ex: %s', key, ex)

    def get(self, key):
        # TODO rename this to get_key (to match set_key)
        try:
            _value = self._data[key]
        except Exception as ex:
            logging.error('Exception while getting key: %s, ex: %s', key, ex)
            _value = None
        return _value
