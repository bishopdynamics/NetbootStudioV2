#!/usr/bin/env python3
"""
Netboot Studio Tasks Manager
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2023 James Bishop (james@bishopdynamics.com)


import uuid
import json
import logging
import asyncio
import pathlib

from NSCommon import NSSafeQueue, start_workers_generic, process_queue_generic
from NSTasks import NSTask_FakeLongTask
from NSTask_BuildiPXE import NSTask_BuildiPXE
from NSTask_Image_WindowsFromISO import NSTask_Image_WindowsFromISO
from NSTask_Image_ESXFromISO import NSTask_Image_ESXFromISO
from NSTask_Image_DebianWeb import NSTask_Image_DebianWeb
from NSTask_Image_UbuntuWeb import NSTask_Image_UbuntuWeb
from NSTask_Image_DebianLive import NSTask_Image_DebianLive
from NSPubSub import NSMQTTClient

# api request places task requests in a staging queue
# TaskWorker pulls requests out of that queue and puts them in its own queue


class NSTaskManager:
    # manage lifecycle of tasks
    tasks_maxthreads = 4  # number of threads on which to process tasks
    staging_maxthreads = 2  # number of threads to handle moving staged tasks to queue
    queue_maxsize = 0  # how large to allow a queue to get, affects all queues, 0 = infinite

    def __init__(self, config, paths, queue_staging, loop):
        self.config = config
        self.paths = paths
        self.loop = loop
        self.queue_staging = queue_staging
        self.mqtt_client_name = 'NSTaskManager_%s' % uuid.uuid4()
        self.mqtt_topic = 'NetbootStudio/TaskStatus'
        self.mqtt_client = NSMQTTClient(self.mqtt_client_name, self.config, self.paths, [(self.mqtt_topic, 0)], self.mqtt_receive, self.loop)
        self.task_map = {
            'build_ipxe': {
                'class': NSTask_BuildiPXE,
                'name': 'Build iPXE',
                'description': 'Build an ipxe binary and iso, and another iso without embedded stage1_file',
            },
            'image_windows_installer_from_iso': {
                'class': NSTask_Image_WindowsFromISO,
                'name': 'New Windows boot image from ISO',
                'description': 'Create a new Windows installer boot image from ISO',
            },
            'image_esx_installer_from_iso': {
                'class': NSTask_Image_ESXFromISO,
                'name': 'New VMware ESXi boot image from ISO',
                'description': 'Create a new VMware ESXi installer boot image from ISO',
            },
            'image_debian_webinstaller': {
                'class': NSTask_Image_DebianWeb,
                'name': 'New Debian Webinstaller',
                'description': 'Create a minimal boot image to fetch and install Debian from the web',
            },
            'image_ubuntu_webinstaller': {
                'class': NSTask_Image_UbuntuWeb,
                'name': 'New Ubuntu Webinstaller',
                'description': 'Create a minimal boot image to fetch and install Ubuntu from the web',
            },
            'image_debian_liveimage': {
                'class': NSTask_Image_DebianLive,
                'name': 'New Debian Liveimage',
                'description': 'Create a bootable live image of Debian',
            },
            'fake_longtask': {
                'class': NSTask_FakeLongTask,
                'name': 'Fake Long Task',
                'description': 'a fake long running task that reports status several times',
            },
        }
        # this needs its own independent loop, created here
        self.loop = asyncio.new_event_loop()
        self.queue_tasks = NSSafeQueue(loop=self.loop, maxsize=self.queue_maxsize)
        self.task_status = []  # store task status here, and let the datasource publish it. we need it as an array so we can use an NSDataSourceTable on the js side
        self.task_index = {}  # track task objects by task_id, until they are cleared
        self.start_task_workers()
        self.start_staging_workers()

    def mqtt_receive(self, topic, msg):
        """
        handle a mqtt message
        :param topic: mqtt topic
        :type topic: str
        :param msg: message
        :type msg: str
        """
        try:
            if topic == self.mqtt_topic:
                message = json.loads(msg)
                if 'task_status' in message:
                    # logging.debug('NSTaskManager received a task status message via mqtt topic')
                    self.send_message(message['task_status'])
        except Exception as ex:
            logging.error('Unexpected Exception while mqtt_receive: %s', ex)

    def get_task_status(self):
        return self.task_status

    def report_queued(self, task_payload: dict):
        try:
            self.send_message({
                'task_id': task_payload['task_id'],
                'task_name': task_payload['task_name'],
                'task_description': task_payload['task_description'],
                'task_type': task_payload['task_type'],
                'task_status': 'Queued',
                'task_progress': 0,
                'task_progress_description': 'awaiting worker availability',
            })
        except Exception as ex:
            logging.exception('unexpected error while reporting task status: %s' % ex)

    def start_task_workers(self):
        # create threads to execute the tasks queue
        logging.info('Starting %s TaskWorkers' % self.tasks_maxthreads)
        start_workers_generic(self.tasks_maxthreads, 'TaskWorker', self.process_tasks_queue)

    def start_staging_workers(self):
        # create threads to move staged tasks into queue
        logging.info('Starting %s TaskStagingWorkers' % self.staging_maxthreads)
        start_workers_generic(self.staging_maxthreads, 'TaskStagingWorker', self.process_staging_queue)

    def process_tasks_queue(self):
        # consume tasks one at a time until there are none left
        process_queue_generic(self.queue_tasks, self.execute_task)

    def process_staging_queue(self):
        # consume tasks one at a time until there are none left
        process_queue_generic(self.queue_staging, self.queue_staged_task)

    def queue_staged_task(self, task_object):
        # move from staging to tasks queue
        #   this is where id, name, and description are added to the payload
        if task_object['task_type'] in self.task_map:
            task_object['task_id'] = str(uuid.uuid4())
            task_object['task_name'] = self.task_map[task_object['task_type']]['name']
            task_object['task_description'] = self.task_map[task_object['task_type']]['description']
            logging.debug('queueing staged task id: %s', task_object['task_id'])
            self.queue_tasks.put(task_object)
            self.report_queued(task_object)
        else:
            logging.info('Ignoring unrecognized task type: %s', task_object['task_type'])

    def send_message(self, task_status: dict):
        # we arent actually going to send a message here, but NSTask objects dont need to know that
        #   we want only one entry per task id in the list, so we go through and create a new list
        #       by iterating and inserting ours new one where the old one was, we hope to maintain order
        found_existing = False
        new_task_status = []
        for existing_task in self.task_status:
            # print(json.dumps(existing_task))
            if existing_task['task_id'] == task_status['task_id']:
                if found_existing:
                    logging.error('found an additional task with id: %s, it will be discarded' % existing_task['task_id'])
                else:
                    new_task_status.append(task_status)
                    found_existing = True
            else:
                new_task_status.append(existing_task)
        if not found_existing:
            new_task_status.insert(0, task_status)
        self.task_status = new_task_status

    def execute_task(self, task_object):
        # run task, reporting running status, and then complete status
        try:
            task_id = task_object['task_id']
            if task_id in self.task_index:
                logging.error(f'An entry in running_tasks already exists for: {task_id}')
                raise Exception(f'An entry in running_tasks already exists for: {task_id}')
            # if task_payload includes a name, rewrite description
            if 'name' in task_object['task_payload']:
                task_object['task_description'] = 'Creating: %s' % task_object['task_payload']['name']
            logging.debug('task_object: %s' % json.dumps(task_object))
            task_class = self.task_map[task_object['task_type']]['class']
            taskobj = task_class(self.paths, self.send_message, task_object)
            self.task_index[task_id] = taskobj
            taskobj.start()
        except Exception as ex:
            logging.exception('failed while execute_task: %s' % ex)

    def get_tasks(self):
        # the DataSource will use this to fetch current status
        return self.task_status

    def task_action(self, task_id, action, payload=None):
        # perform some action on a task
        # stop, retry, clear, log
        logging.debug(f'task_action called: {task_id}, {action}')
        try:
            if action == 'clear':
                # call task.cleanup() and then remove from task_index
                logging.info(f'Clearing task: {task_id}')
                self.task_index[task_id].cleanup()
                self.task_index.pop(task_id)
                for index, existing_task in enumerate(self.task_status):
                    if existing_task['task_id'] == task_id:
                        self.task_status.pop(index)
                        break
            elif action == 'stop':
                logging.info(f'Stopping task: {task_id}')
                self.task_index[task_id].stop()
            elif action == 'log':
                # get the current content of the log
                # need to figure out where the log is
                # it would be really cool if we could stream logfile contents, one line at a time on a bespoke mqtt topic, 
                #   and then client-side we just append all messages received to a running buffer
                # but realistically we should just fetch static file content, and have a re-fetch button
                log_file = self.task_index[task_id].log_file
                if log_file is None:
                    raise Exception('failed to fetch log file, path is None')
                if not pathlib.Path(log_file).is_file():
                    raise Exception('failed to fetch log file, not found')
                content = ''
                with open(log_file, 'r', encoding='utf-8') as lf:
                    content = lf.read()
                return_obj = {
                    'log_file': str(log_file),
                    'log_content': content,
                }
                return return_obj
            else:
                raise Exception(f'unknown task action: {action}')
            return True
        except Exception as ex:
            logging.exception('exception while task_action: %s' % ex)
            return False