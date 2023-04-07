#!/usr/bin/env python3
"""
Netboot Studio Tasks
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2023 James Bishop (james@bishopdynamics.com)

import os
import sys
import logging
import time
import platform
import tempfile
import pathlib
import uuid
import shutil
import subprocess
import threading
import yaml
import trace


from configparser import RawConfigParser

from abc import abstractmethod
from collections import OrderedDict

from NSCommon import NSMessage, get_timestamp, sanitize_string, check_config


class StoppableThread(threading.Thread):
    # Thread that can be stopped, using trace
    #   calling join() will return the result
    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self.killed = False
        self._return = None
        self.has_returned = False

    def run(self):
        # override run() so we can set a trace and capture return
        sys.settrace(self.globaltrace)
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)
            self.has_returned = True

    def globaltrace(self, frame, event, arg):
        if event == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, event, arg):
        if self.killed:
            if event == 'line':
                raise SystemExit()
        return self.localtrace

    def stop(self):
        self.killed = True

    def join(self, *args):
        if not self.has_returned:
            threading.Thread.join(self, *args)
        return self._return


class NSTask:
    # base class for tasks
    #   you must implement start_task and stop_task
    #       also implement __init__(self, paths: dict, send_message, task_object: dict)
    #           and call super().__init__(self, paths: dict, send_message, task_object: dict)
    #       use self.progress_update(int, str) to update progress
    #       call self.complete_task() when done
    required_keys = []  # declare required keys an they will be checked at init
    config = RawConfigParser()
    # These are the only valid status values
    valid_status = {
        'Queued',
        'Initialized',
        'Starting',
        'Running',
        'Stopping',
        'Complete',
        'Failed',
    }

    def __init__(self, paths: dict, send_message, task_object: dict):
        self.paths = paths
        self.send_message = send_message
        self.task_payload = task_object['task_payload']
        self.task_name = task_object['task_name']
        self.task_description = task_object['task_description']
        self.task_type = task_object['task_type']
        self.task_id = task_object['task_id']
        self.config.read(self.paths['config.ini'])
        self.service_user = self.config.get('main', 'service_user')
        self.service_group = self.config.get('main', 'service_group')
        self.service_uid = self.config.get('main', 'service_uid')
        self.service_gid = self.config.get('main', 'service_gid')
        self.subtasks = OrderedDict()
        self.subtask_status = OrderedDict()
        self.task_timestamp_init = get_timestamp()
        self.task_timestamp_start = ''
        self.task_timestamp_stop = ''
        self.task_timestamp_end = ''
        self.current_subtask_name = ''
        self.subtasks = self.get_subtasks()
        self.subtask_descriptions = OrderedDict()
        for subtask_name, subtask_obj in self.subtasks.items():
            self.subtask_descriptions[subtask_name] = subtask_obj['description']
        self.should_stop = False  # checked regularly while running task, will stop and fail if ever True
        self.running_thread = None  # the current running subtask thread
        self.report_status('Initialized', 0, 'Initialized')

    def check_required_keys(self):
        all_ok = True
        for keyname in self.required_keys:
            if keyname not in self.task_payload:
                logging.error('missing required key in task_payload: %s' % keyname)
                all_ok = False
                break
        return all_ok

    def report_status(self, status: str, progress: int, description: str):
        try:
            if status not in self.valid_status:
                logging.warning(f'Encountered unknown task status: {status}')
            if status == 'Complete':
                current_subtask = ''
            else:
                current_subtask = self.current_subtask_name
            message = {
                'task_id': self.task_id,
                'task_name': self.task_name,
                'task_description': self.task_description,
                'task_type': self.task_type,
                'task_status': status,
                'task_progress': progress,
                'task_progress_description': description,
                'task_current_subtask': current_subtask,
                'task_subtask_descriptions': self.subtask_descriptions
            }
            self.send_message(message)
        except Exception as ex:
            logging.exception('unexpected error while reporting task status: %s' % ex)

    def progress_update(self, progress: int, description: str):
        self.report_status('Running', progress, description)

    def start(self):
        # TODO if a subtask lacks progress, then increase by 100/numsubtasks
        # TODO if we run the function in a thread, and then wait for it, we can kill it if stop() is called
        logging.info('Starting Task: %s' % self.task_id)
        self.report_status('Starting', 0, 'Starting subtasks')
        self.task_timestamp_start = get_timestamp()
        task_succeeded = True
        if self.should_stop:
            # if initalizer marked this task not to start, then go ahead and fail
            self.fail_task('failed to initialize')
            return
        if self.check_required_keys():
            for subtask_name, subtask_obj in self.subtasks.items():
                logging.debug('running subtask: %s' % subtask_name)
                self.current_subtask_name = subtask_name
                self.progress_update(subtask_obj['progress'], subtask_obj['description'])
                # result = subtask_obj['function']()
                self.running_thread = StoppableThread(target=subtask_obj['function'])
                self.running_thread.start()
                was_stopped = False
                while not self.running_thread.has_returned:
                    time.sleep(2)
                    if self.should_stop:
                        logging.debug('should_stop = True, killing thread')
                        was_stopped = True
                        self.running_thread.stop()
                        break
                result = self.running_thread.join()
                if was_stopped:
                    self.subtask_status[subtask_name] = 'Failed'
                    self.fail_task('stopped by user')
                    task_succeeded = False
                    break
                if not result:
                    self.subtask_status[subtask_name] = 'Failed'
                    self.fail_task('subtask failed: %s' % subtask_name)
                    task_succeeded = False
                    break
                else:
                    logging.debug('subtask: %s suceeded' % subtask_name)
                    self.subtask_status[subtask_name] = 'Success'
            if task_succeeded:
                self.complete_task()

    def stop(self):
        # stop (interrupt) task, but DO NOT cleanup
        logging.info('Stopping Task: %s' % self.task_id)
        self.report_status('Stopping', 0, 'trying to stop task')
        self.task_timestamp_stop = get_timestamp()
        self.should_stop = True

    def complete_task(self):
        logging.info('Completed Task: %s' % self.task_id)
        self.report_status('Complete', 100, 'Success')
        self.task_timestamp_end = get_timestamp()

    def fail_task(self, message):
        self.should_stop = True
        self.report_status('Failed', 100, message)
        logging.error('Failed Task: %s : %s' % (self.task_id, message))

    def fake_subtask(self):
        # this should never be used, because get_subtasks must be overriden; it exists to satisfy linter
        return False

    @abstractmethod
    def get_subtasks(self):
        # they are defined like this because self.subtasks is an ordered dict and we want to preserve order
        #   function must take no arguments and return True or False
        self.subtasks = OrderedDict({
            'fake_subtask': {
                'description': 'faking subtask because get_subtasks was not overriden',
                'progress': 1,
                'function': self.fake_subtask,
            },
        })
        return self.subtasks

    @abstractmethod
    def cleanup(self):
        # clean up any temp resources
        # to be optionally implemented by sub-class
        return


class NSTask_FakeLongTask(NSTask):
    # fake job that pretends to do some work and reports status
    required_keys = []  # declare required keys an they will be checked at init

    def get_subtasks(self):
        # they are defined like this because self.subtasks is an ordered dict and we want to preserve order
        #   function must take no arguments and return True or False
        self.subtasks = OrderedDict({
            'prepare_nucleotides': {
                'description': 'Preparing Nucleotides',
                'progress': 10,
                'function': self.prepare_nucleotides,
            },
            'reticulate_splines': {
                'description': 'Reticulating Splines',
                'progress': 20,
                'function': self.reticulate_splines,
            },
            'popularize_actor_pool': {
                'description': 'Popularizing Actor Pool',
                'progress': 30,
                'function': self.popularize_actor_pool,
            },
            'energize_stansifram': {
                'description': 'Energizing Stanisfram',
                'progress': 50,
                'function': self.energize_stansifram,
            },
            'compile_phase_modules': {
                'description': 'Compiling Phase Modules',
                'progress': 70,
                'function': self.compile_phase_modules,
            },
            'verify_files': {
                'description': 'Verifying Files',
                'progress': 90,
                'function': self.verify_files,
            },
        })
        return self.subtasks

    def prepare_nucleotides(self):
        time.sleep(2)
        return True

    def reticulate_splines(self):
        time.sleep(2)
        return True

    def popularize_actor_pool(self):
        time.sleep(1)
        return True

    def energize_stansifram(self):
        time.sleep(2)
        return True

    def compile_phase_modules(self):
        time.sleep(5)
        return True

    def verify_files(self):
        time.sleep(1)
        return True


class NSTask_Builder(NSTask):
    # base class for builders
    #   provides standardized methods for common build-related tasks
    build_dependencies = []

    def __init__(self, paths, mqtt_client, task_payload):
        super().__init__(paths, mqtt_client, task_payload)
        self.log_file = None
        self.temp_dir = None
        try:
            self.boot_images = self.paths['boot_images']
            self.ssl_ca_cert = self.paths['ssl_ca_cert']
            self.ssl_full_chain = self.paths['ssl_full_chain']
            self.build_id = str(uuid.uuid4())
            self.temp_dir = pathlib.Path(tempfile.mkdtemp(dir=self.paths['temp']))
            self.log_file = self.temp_dir.joinpath('build.log')
            self.log_msg(f'log_file: {str(self.log_file)}')
            logging.debug(f'log_file: {str(self.log_file)}')
        except Exception as ex:
            logging.error('Exception while initializing: %s' % ex)
            return False
        # to be filled in later
        self.created = get_timestamp()
        self.workspace = None  # hold output while being built
        self.scratch = None  # temp space for stuff that should not be in final output

    # ################## Start of subtask methods ########################################

    def check_dependencies(self):
        # check that each of the commmands we need are available
        # this assumes we running in the docker container
        missing_deps = []
        self.log_msg('checking dependencies')
        try:
            if platform.system() != 'Linux':
                logging.error('only support creating boot images on Linux host')
                return False
            for _dep in self.build_dependencies:
                try:
                    result = self.run_cmd('command -v %s' % _dep, skip_logfile=True)
                except:
                    self.log_error(f'Failed to find dependency: {_dep}')
                if result.returncode > 0:
                    missing_deps.append(_dep)
            if missing_deps:
                logging.error(f'task {self.task_type} needs some commands which are missing: {str(missing_deps)}')
                # logging.error('  %s' % self.build_dep_help)
                return False
            else:
                return True
        except Exception as ex:
            logging.error('Exception while check_dependencies: %s' % ex)
            return False

    def create_workspace(self):
        # check if boot image already exists, then create temporary workspace
        #   workspace is where we create our image, before moving it into boot_images/
        try:
            self.workspace = self.temp_dir.joinpath('workspace')
            self.workspace.mkdir()
            self.log_msg(f'workspace: {str(self.workspace)}')
            return True
        except Exception as ex:
            logging.error('Exception while create_workspace: %s' % ex)
            return False

    def create_scratch(self):
        # create temporary scratch folder
        #   scratch is for temporary stuff that should not be in the final image
        #   and will be deleted by finalize_and_cleanup
        try:
            self.scratch = self.temp_dir.joinpath('scratch')
            self.scratch.mkdir()
            self.log_msg(f'scratch: {str(self.scratch)}')
            return True
        except Exception as ex:
            logging.error('Exception while create_scratch: %s' % ex)
            return False

    @abstractmethod
    def write_metadata(self):
        # create metadata.yaml
        # Must be implemented by subclass!
        raise NotImplementedError

    # ################## End of subtask methods ########################################

    def write_to_file(self, file, content):
        # just a dumb wrapper to write to a file
        with open(file, 'wt', encoding='utf-8') as fc:
            fc.write(content)

    def append_to_file(self, file, content):
        # just a dumb wrapper to append to a file
        with open(file, 'at', encoding='utf-8') as fc:
            fc.write(content)

    def cleanup(self):
        # clean up any temp resources
        self.log_msg(f'Cleaning up temporary files at {self.temp_dir}')
        self.workspace = None
        self.scratch = None
        # NOTE shutil.rmtree() does not work, it takes FOREVER, dont know why it is so slow
        if self.temp_dir is not None:
            if pathlib.Path(self.temp_dir).is_dir():
                logging.debug(f'Deleting folder: {self.temp_dir}')
                self.run_cmd('rm -r "%s"' % self.temp_dir)
        self.temp_dir = None

    def run_cmd(self, cmd, cwd=None, skip_logfile=False):
        # given a string representing command and arguments, run it and return an object you can deal with
        # the only purpose of this is to provide a single place to change our approach to running commands
        # subprocess.run() does not raise an exception if the underlying process errors!
        # shell=True is needed so that command -v works. It is a security risk, we should move as many things to pythony instead of bashy
        environment = os.environ.copy()
        # /usr/local/bin:/usr/bin:/bin
        environment['PATH'] = '/usr/sbin:/sbin:%s' % environment['PATH']
        # we redirect stderr to stdout using 2>&1 , so that both are in the same output and in order
        logging.info('running command:[%s] %s' % (cwd, cmd))
        if skip_logfile:
            # just run the command blindly. we still capture all output so it can be read from result.stdout
            result = subprocess.run('%s 2>&1' % cmd, shell=True, universal_newlines=True, cwd=cwd, capture_output=True, text=True, env=environment)
        else:
            # write the output live to the log file, but not to the console
            logging.info('Output will be written to log file: %s' % self.log_file)
            lf = open(self.log_file, 'a')
            result = subprocess.run('%s 2>&1' % cmd, shell=True, universal_newlines=True, cwd=cwd, text=True, env=environment, stdout=lf, stderr=lf)
            lf.close()
        if result.returncode != 0:
            if not skip_logfile:
                raise Exception('run_cmd failed, check log file: %s' % self.log_file)
            else:
                raise Exception('run_cmd failed and wasnt logged to a file')
        return result

    def log_msg(self, msg, error=False):
        # write some text to the log file, followed by a blank line
        #   also print the message
        print(msg)
        if error:
            logging.error('NSTask_image_windows-from-iso error: %s' % msg)
        if self.log_file is not None:
            with open(self.log_file, 'a+') as lf:
                lf.write(msg)
                lf.write('\n\n')

    def log_error(self, msg):
        # log an error to the file, also throw an exception (so use this in a try block)
        logging.error(msg)
        logging.error('check log in workspace: %s' % str(self.log_file))
        self.log_msg(msg, error=True)
        raise Exception(msg)


class NSTask_Image_Builder(NSTask_Builder):
    # base class for image builders
    build_dependencies = [
        '7z',
    ]

    def __init__(self, paths, mqtt_client, task_payload):
        super().__init__(paths, mqtt_client, task_payload)
        self.iso_file = None
        try:
            self.boot_image_name = sanitize_string(self.task_payload['name'])
            if self.boot_image_name == '':
                raise Exception('boot image name is empty!')
            self.log_msg(f'boot_image_name: {self.boot_image_name}')
            self.boot_image_path = self.boot_images.joinpath(self.boot_image_name)
            if self.boot_image_path.is_dir():
                raise Exception('boot image folder already exists: %s' % str(self.boot_image_path))
        except Exception as ex:
            self.should_stop = True
            logging.error('Exception while initializing: %s' % ex)
            return False
        self.bootimage_metadata = {
            'created': self.created,
            'image_type': '',
            'description': '',
            'arch': '',
            'release': '',
            'stage2_filename': 'stage2.ipxe',
            'supports_unattended': False,
        }

    def extract_iso(self):
        # extract ISO into workspace using 7z
        try:
            self.iso_file = self.paths['iso'].joinpath(self.task_payload['iso_file'])
            self.log_msg(f'using iso: {str(self.iso_file)}')
            if not self.iso_file.is_file():
                self.log_error('could not find iso file: %s' % str(self.iso_file))
            result_extract = self.run_cmd(f'7z x -o"{str(self.workspace)}" "{str(self.iso_file)}"', self.workspace)
            if result_extract.returncode > 0:
                self.log_error('failed to extract iso!')
            return True
        except Exception as ex:
            logging.error('Exception while extract_iso: %s' % ex)
            return False

    def write_metadata(self):
        # create metadata.yaml
        try:
            self.log_msg('writing metadata.yaml')
            meta_file = self.workspace.joinpath('metadata.yaml')
            with open(meta_file, 'w', encoding='utf-8') as mf:
                yaml.dump(self.bootimage_metadata, mf)
            return True
        except Exception:
            logging.exception('Unexpected exception while writing metadata.json')
            return False

    def finalize_and_cleanup(self):
        # finalize our image by moving it into boot_images/ and cleaning up temp folders
        #   NOTE this should ALWAYS be the last step of building an image
        try:
            if self.boot_image_path.is_dir():
                logging.error('existing boot image folder appeared since we checked at beginning of task!')
                self.log_error('boot image folder already exists: %s' % str(self.boot_image_path))
            self.log_msg(f'Moving {str(self.workspace)} to {str(self.boot_image_path)}')
            shutil.move(self.workspace, self.boot_image_path)
            new_log_file = self.boot_image_path.joinpath('netbootstudio-bootimage-build.log')
            shutil.copy(self.log_file, new_log_file)
            self.log_file = new_log_file
            self.run_cmd(f'chown -R {self.service_uid}:{self.service_gid} .', self.boot_image_path)
            self.cleanup()
            return True
        except Exception as ex:
            logging.error('Exception while finalize_and_cleanup: %s' % ex)
            return False