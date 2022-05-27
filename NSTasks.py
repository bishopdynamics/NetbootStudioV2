#!/usr/bin/env python3
"""
Netboot Studio Tasks
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2021 James Bishop (james@bishopdynamics.com)

import logging
import time

from abc import abstractmethod
from collections import OrderedDict

from NSCommon import NSMessage, get_timestamp


class NSTask:
    # base class for tasks
    #   you must implement start_task and stop_task
    #       also implement __init__(self, paths: dict, send_message, task_object: dict)
    #           and call super().__init__(self, paths: dict, send_message, task_object: dict)
    #       use self.progress_update(int, str) to update progress
    #       call self.complete_task() when done
    required_keys = []  # declare required keys an they will be checked at init

    def __init__(self, paths: dict, send_message, task_object: dict):
        self.paths = paths
        self.send_message = send_message
        self.task_payload = task_object['task_payload']
        self.task_name = task_object['task_name']
        self.task_description = task_object['task_description']
        self.task_type = task_object['task_type']
        self.task_id = task_object['task_id']
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
        logging.info('Starting Task: %s' % self.task_id)
        self.report_status('Starting', 0, 'Starting subtasks')
        self.task_timestamp_start = get_timestamp()
        if self.check_required_keys():
            for subtask_name, subtask_obj in self.subtasks.items():
                logging.debug('running subtask: %s' % subtask_name)
                self.current_subtask_name = subtask_name
                self.progress_update(subtask_obj['progress'], subtask_obj['description'])
                result = subtask_obj['function']()
                if not result:
                    self.subtask_status[subtask_name] = 'Fail'
                    self.fail_task('subtask failed: %s' % subtask_name)
                else:
                    logging.debug('subtask: %s suceeded' % subtask_name)
                    self.subtask_status[subtask_name] = 'Success'
            self.complete_task()

    def stop(self):
        logging.info('Stopping Task: %s' % self.task_id)
        self.report_status('Stopping', 0, 'trying to stop task')
        self.task_timestamp_stop = get_timestamp()
        # TODO figure out how task stopping works
        logging.error('Task Stopping is not implemented')
        raise NotImplementedError

    def complete_task(self):
        logging.info('Completed Task: %s' % self.task_id)
        self.report_status('Complete', 100, 'Success')
        self.task_timestamp_end = get_timestamp()

    def fail_task(self, message):
        self.report_status('Failed', 0, message)
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
