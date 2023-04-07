#!/usr/bin/env python3
"""
Netboot Studio Messages Processor
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2023 James Bishop (james@bishopdynamics.com)

# TODO we have methods with build_ in their name that have nothing to do with building binaries, this is confusing vocab
# TODO tftp_root functions are not fleshed out

import json
import os
import shutil
import subprocess

import logging
import pathlib

from aiohttp import web

from NSCommon import NSMessage


class NSMessageProcessor:
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
        'stage4': [
            {
                'filename': 'none',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: no script',
            },
            {
                'filename': 'stage4-entry-unix.sh',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: entrypoint for unix-style systems',
            },
            {
                'filename': 'stage4-entry-windows.bat',
                'modified': '1970-01-01_00:00:00',
                'description': 'builtin: entrypoint for windows systems',
            },
        ],
    }

    def __init__(self, config, paths, q_staging, client_mgr, file_mgr, task_mgr):
        self.config = config  # unused
        self.paths = paths
        self.q_staging = q_staging
        self.client_manager = client_mgr
        self.file_manager = file_mgr
        self.task_manager = task_mgr
        self.endpoint_methods = {
            'get_ipxe_builds': self.get_ipxe_builds,
            'get_stage1_files': self.get_stage1_files,
            'get_uboot_scripts': self.get_uboot_scripts,
            'get_boot_images': self.get_boot_images,
            'get_unattended_configs': self.get_unattended_configs,
            'get_client': self.get_client,
            'get_clients': self.get_clients,
            'set_client_config': self.set_client_config,
            'set_client_info': self.set_client_info,
            'create_task': self.create_task,
            'delete_client': self.delete_client,
            'delete_boot_image': self.delete_boot_image,
            'delete_unattended_config': self.delete_unattended_config,
            'delete_ipxe_build': self.delete_ipxe_build,
            'delete_wimboot_build': self.delete_wimboot_build,
            'delete_stage1_file': self.delete_stage1_file,
            'delete_uboot_script': self.delete_uboot_script,
            'delete_iso': self.delete_iso,
            'delete_stage4': self.delete_stage4,
            'get_settings': self.get_settings,
            'set_settings': self.set_settings,
            'task_action': self.task_action,
            'get_file': self.get_file,
            'save_file': self.save_file,
        }

    # these two methods are the core of api handling
    def handle(self, _msg, origin, topic=None):
        try:
            msg = NSMessage(_msg)
            msg.set('origin', origin)
            msg.set('topic', topic)
        except Exception as e:
            logging.error('unexpected exception while parsing NSMessage from string: %s' % e)
            return False
        else:
            if msg.get('topic') == 'api_request':
                # handle an api request
                res = self.handle_api(msg)
                return res
            else:
                logging.info('dont know how to handle message topic: %s', msg.get('topic'))
                return False

    def handle_api(self, request_message):
        # This does all the meat of handling an API request
        origin = None
        req_id = None
        payload = None
        endpoint = None
        try:
            origin = request_message.get('origin')
            content = request_message.get('content')
            req_id = content['id']
            endpoint = content['endpoint']
            payload = content['api_payload']
            if endpoint in self.endpoint_methods:
                endpoint_method = self.endpoint_methods[endpoint]
                response = endpoint_method(payload)
            else:
                logging.error('unrecognized api endpoint: %s' % endpoint)
                response = self.build_error('unrecognized endpoint')
        except Exception:
            logging.exception('Unexpected exception while processing api call')
            response = self.build_error('internal server exception')
        # response has status,api_payload
        #   need to decorate with additional info
        response['id'] = req_id
        response['endpoint'] = endpoint
        response['request_payload'] = payload
        try:
            # Now we send our reply
            if origin == 'webserver':
                # need to return a web.Response object
                return web.Response(text=json.dumps(response), status=response['status'])
            elif origin == 'broker':
                # came from mqtt broker, we need to respond with an NSMessage (as json string)
                response_msg = NSMessage()
                response_msg.set('topic', 'api_response')
                response_msg.set('origin', 'NSMessageProcessor')
                response_msg.set('content', response)
                return response_msg.to_json()
            else:
                logging.warning('dont know how to respond when origin = %s' % response['origin'])
                return False
        except Exception:
            logging.exception('Unexpected exception while responding to api call')
            return False

    # these methods are helpers
    @staticmethod
    def build_response(response_type, result):
        if response_type == 'success':
            response = {
                'status': 200,
                'api_payload': {
                    'result': result
                },
            }
        else:
            response = {
                'status': 500,
                'api_payload': {
                    'error': result
                },
            }
        return response

    def build_success(self, result):
        return self.build_response('success', result)

    def build_error(self, error):
        return self.build_response('error', error)

    # these are endpoint_methods
    def get_stage1_files(self, payload):
        if len(dict(payload)) > 0:
            logging.warning('this endpoint does not take any payload keys')
        stage1_files = self.file_manager.get_files('stage1_files')
        return self.build_success(stage1_files)

    def get_uboot_scripts(self, payload):
        if len(dict(payload)) > 0:
            logging.warning('this endpoint does not take any payload keys')
        uboot_scripts = self.file_manager.get_files('uboot_scripts')
        return self.build_success(uboot_scripts)

    def get_unattended_configs(self, payload):
        if len(dict(payload)) > 0:
            logging.warning('this endpoint does not take any payload keys')
        unattended_configs = self.file_manager.get_files('unattended_configs')
        return self.build_success(unattended_configs)

    def get_boot_images(self, payload):
        if len(dict(payload)) > 0:
            logging.warning('this endpoint does not take any payload keys')
        boot_images = self.file_manager.get_files('boot_images')
        return self.build_success(boot_images)

    def get_ipxe_builds(self, payload):
        if len(dict(payload)) > 0:
            logging.warning('this endpoint does not take any payload keys')
        ipxe_builds = self.file_manager.get_files('ipxe_builds')
        return self.build_success(ipxe_builds)

    def set_client_config(self, payload):
        try:
            payload = dict(payload)
            client_mac = payload['mac']
            config_dict = payload['config']
            logging.debug('setting client config for mac: %s' % client_mac)
        except KeyError:
            logging.error('api call to set_client_config missing needed keys in payload: %s' % json.dumps(payload))
            response = self.build_error('missing needed keys in payload')
        else:
            try:
                self.client_manager.set_client_config(client_mac, config_dict)
            except Exception:
                logging.exception('unexpected exception while set_client_config')
                response = self.build_error('unexpected exception in set_client_config')
            else:
                logging.debug('successfully updated config for client with mac: %s' % client_mac)
                response = self.build_success('Success')
        return response

    def set_client_info(self, payload):
        try:
            payload = dict(payload)
            client_mac = payload['mac']
            info_dict = payload['info']
            logging.debug('setting client config for mac: %s' % client_mac)
        except KeyError:
            logging.error('api call to set_client_config missing needed keys in payload: %s' % json.dumps(payload))
            response = self.build_error('missing needed keys in payload')
        else:
            try:
                self.client_manager.set_client_info(client_mac, info_dict)
            except Exception:
                logging.exception('unexpected exception while set_client_info')
                response = self.build_error('unexpected exception in set_client_info')
            else:
                logging.debug('successfully updated info for client with mac: %s' % client_mac)
                response = self.build_success('Success')
        return response

    def get_client(self, payload):
        # get all client information and config
        try:
            payload = dict(payload)
            client_mac = payload['mac']
            logging.debug('getting client config for mac: %s' % client_mac)
            all_props = self.client_manager.get_client(client_mac)
        except Exception as ex:
            logging.exception('unexpected exception while get_client_config: %s' % ex)
            response = self.build_error('error while get_client_config')
        else:
            response = self.build_success(all_props)
        return response

    def get_clients(self, payload):
        if len(dict(payload)) > 0:
            logging.warning('this endpoint does not take any payload keys')
        result = self.client_manager.get_clients()
        return self.build_success(result)

    def create_task(self, payload):
        # throw task into staging queue for taskmanager to pick up
        try:
            payload = dict(payload)
            self.q_staging.put(payload)
            return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception while create_task: %s' % ex)
            return self.build_error('unexpected exception in create_task')

    def task_action(self, payload):
        # request task manager to perform an action on a specific task
        try:
            payload = dict(payload)
            task_id = payload['task_id']
            action = payload['action']
            logging.debug(f'handling task_action for: {action}, {task_id}')
            result = self.task_manager.task_action(task_id, action)
            if not result:
                raise Exception('task action failed')
            if action == 'log':
                return self.build_success(result)
            return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception while create_task: %s' % ex)
            return self.build_error('unexpected exception in create_task')

    def delete_folder(self, folderpath):
        # delete a folder and its contents
        # NOTE shutil.rmtree() does not work, it takes FOREVER, dont know why it is so slow
        logging.debug(f'Deleting folder: {folderpath}')
        if folderpath is None:
            raise Exception(f'given folderpath was: None')
        if not pathlib.Path(folderpath).is_dir():
            raise Exception(f'could not find folder to delete: {folderpath}')
        result = subprocess.run(f'rm -r "{folderpath}"', shell=True, universal_newlines=True, cwd=None, capture_output=False, text=True)
        if result.returncode != 0:
            raise Exception(f'failed to delete_folder: {folderpath}')

    def delete_file(self, filepath):
        # detete a file
        logging.debug(f'Deleting file: {filepath}')
        if filepath is None:
            raise Exception(f'given filepath was: None')
        if not pathlib.Path(filepath).is_file():
            raise Exception(f'could not find file to delete: {filepath}')
        os.remove(filepath)

    def delete_client(self, payload):
        try:
            payload = dict(payload)
            mac = payload['mac']
            self.client_manager.delete_client(mac)
            return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception whle delete_client: %s' % ex)
            return self.build_error('unexpected exception in delete_client')

    def delete_boot_image(self, payload):
        try:
            
            payload = dict(payload)
            boot_image_name = payload['name']
            logging.info(f'Deleting boot image: {boot_image_name}')
            for this_builtin in self.builtin_files['boot_images']:
                if this_builtin['boot_image_name'] == boot_image_name:
                    raise Exception('cannot delete builtins')
            if '.ipxe' in boot_image_name:
                fullpath = pathlib.Path(self.paths['boot_images']).joinpath(boot_image_name)
                self.delete_file(fullpath)
                return self.build_success('Success')
            else:
                fullpath = pathlib.Path(self.paths['boot_images']).joinpath(boot_image_name)
                self.delete_folder(fullpath)
                return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception while delete_boot_image: %s' % ex)
            return self.build_error('unexpected exception in delete_boot_image')

    def delete_unattended_config(self, payload):
        try:
            payload = dict(payload)
            filename = payload['filename']
            for this_builtin in self.builtin_files['unattended_configs']:
                if this_builtin['filename'] == filename:
                    raise Exception('cannot delete builtins')
            fullpath = pathlib.Path(self.paths['unattended_configs']).joinpath(filename)
            self.delete_file(fullpath)
            return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception while delete_unattended: %s' % ex)
            return self.build_error('unexpected exception in delete_unattended_config')

    def delete_ipxe_build(self, payload):
        try:
            payload = dict(payload)
            build_id = payload['build_id']
            fullpath = pathlib.Path(self.paths['ipxe_builds']).joinpath(build_id)
            self.delete_folder(fullpath)
            return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception while delete_ipxe_build: %s' % ex)
            return self.build_error('unexpected exception in delete_ipxe_build')

    def delete_wimboot_build(self, payload):
        try:
            payload = dict(payload)
            build_id = payload['build_id']
            fullpath = pathlib.Path(self.paths['wimboot_builds']).joinpath(build_id)
            self.delete_folder(fullpath)
            return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception while delete_wimboot_build: %s' % ex)
            return self.build_error('unexpected exception in delete_wimboot_builds')

    def delete_stage1_file(self, payload):
        try:
            payload = dict(payload)
            filename = payload['filename']
            for this_builtin in self.builtin_files['stage1_files']:
                if this_builtin['filename'] == filename:
                    raise Exception('cannot delete builtins')
            fullpath = pathlib.Path(self.paths['stage1_files']).joinpath(filename)
            self.delete_file(fullpath)
            return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception while delete_stage1_file: %s' % ex)
            return self.build_error('unexpected exception in delete_stage1_file')

    def delete_stage4(self, payload):
        try:
            payload = dict(payload)
            filename = payload['filename']
            for this_builtin in self.builtin_files['stage4']:
                if this_builtin['filename'] == filename:
                    raise Exception('cannot delete builtins')
            fullpath = pathlib.Path(self.paths['stage4']).joinpath(filename)
            self.delete_file(fullpath)
            return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception while delete_stage4: %s' % ex)
            return self.build_error('unexpected exception in delete_stage4')

    def delete_uboot_script(self, payload):
        try:
            payload = dict(payload)
            filename = payload['filename']
            for this_builtin in self.builtin_files['uboot_scripts']:
                if this_builtin['filename'] == filename:
                    raise Exception('cannot delete builtins')
            fullpath = pathlib.Path(self.paths['uboot_scripts']).joinpath(filename)
            self.delete_file(fullpath)
            return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception while delete_uboot_script: %s' % ex)
            return self.build_error('unexpected exception in delete_uboot_script')

    def delete_iso(self, payload):
        try:
            payload = dict(payload)
            filename = payload['filename']
            fullpath = pathlib.Path(self.paths['iso']).joinpath(filename)
            self.delete_file(fullpath)
            return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception while delete_iso: %s' % ex)
            return self.build_error('unexpected exception in delete_iso')

    def get_settings(self, payload):
        # get application settings
        try:
            logging.debug('getting settings')
            settings = self.client_manager.get_settings()
        except Exception as ex:
            logging.exception('unexpected exception while get_settings: %s' % ex)
            response = self.build_error('error while get_settings')
        else:
            response = self.build_success(settings)
        return response

    def set_settings(self, payload):
        # set applications settings
        try:
            logging.debug('setting settings')
            payload = dict(payload)
            self.client_manager.set_settings(payload['settings'])
            return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception while set_settings: %s' % ex)
            return self.build_error('unexpected exception in set_settings')

    def check_if_builtin(self, file_category, file_name):
        # check if file_name is a builtin for a category
        if file_category not in self.builtin_files:
            return False
        for entry in self.builtin_files[file_category]:
            if entry['filename'] == file_name:
                return True
        return False

    def get_file(self, payload):
        # get content from a file
        # TODO check builtins for this category, prohibit touching builtins
        try:
            payload = dict(payload)
            file_name = payload['file_name']
            file_cat = payload['file_category']
            logging.debug(f'getting a file: {file_cat} / {file_name}')
            if file_cat not in self.paths:
                raise Exception(f'Unknown file_category: {file_cat}')
            if self.check_if_builtin(file_cat, file_name):
                raise Exception(f'Cannot get file: {file_name}, is builtin!')
            base_path = pathlib.Path(self.paths[file_cat])
            file_path = base_path.joinpath(file_name)
            if not file_path.is_file():
                raise Exception(f'File not found: {file_path}')
            logging.debug(f'reading from file: {file_path}')
            file_content = ''
            with open(file_path, 'r', encoding='utf-8') as fp:
                file_content = fp.read()
            return_obj = {
                'file_name': file_name,
                'file_category': file_cat,
                'file_path': str(file_path),
                'file_content': file_content,
            }
            return self.build_success(return_obj)
        except Exception as ex:
            logging.exception('exception while get_file: %s' % ex)
            return self.build_error('unexpected exception in get_file')

    def save_file(self, payload):
        # write content to a file
        # TODO check builtins for this category, prohibit touching builtins
        try:
            payload = dict(payload)
            file_name = payload['file_name']
            file_cat = payload['file_category']
            logging.debug(f'saving a file: {file_cat} / {file_name}')
            if file_cat not in self.paths:
                raise Exception(f'Unknown file_category: {file_cat}')
            if self.check_if_builtin(file_cat, file_name):
                raise Exception(f'Cannot write to file: {file_name}, is builtin!')
            base_path = pathlib.Path(self.paths[file_cat])
            file_path = base_path.joinpath(file_name)
            if not file_path.is_file():
                raise Exception(f'File not found: {file_path}')
            logging.debug(f'writing to file: {file_path}')
            file_content = payload['file_content']
            with open(file_path, 'w', encoding='utf-8') as fp:
                fp.write(file_content)
            return self.build_success('Success')
        except Exception as ex:
            logging.exception('exception while save_file: %s' % ex)
            return self.build_error('unexpected exception in save_file')
