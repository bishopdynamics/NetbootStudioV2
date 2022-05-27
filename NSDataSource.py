#!/usr/bin/env python3
"""
Netboot Studio Data Source
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2021 James Bishop (james@bishopdynamics.com)
import asyncio
import json
import logging
import uuid

from NSPubSub import NSMQTTClient


class NSDataSource:
    # Data source type can be either "provider" or "consumer". a provider takes care of regularly updating the value, a consumer maintains the local value via updates from the provider
    # for a provider, the_function is called every cycle_time seconds and if the value has changed that change is published
    # for a consumer, the_function is called with the new value if the value changes
    #   a consumer can provide None as the_function, to not get notified (use .get_value() instead)

    def __init__(self, config, paths, loop, name, source_type, the_function=None, scan_cycle=1):
        self.config = config
        self.paths = paths
        self.loop = loop
        self.source_type = source_type
        self.the_function = the_function
        self.scan_cycle = scan_cycle
        self.name = name
        logging.debug('setting up data source: %s' % self.name)
        self.mqtt_client_name = '%s_%s_%s' % (self.name, self.source_type, uuid.uuid4())
        self.value = {}
        self.value_json = json.dumps(self.value)
        self.mqtt_topic = 'NetbootStudio/DataSources/%s' % name
        self.mqtt_client = NSMQTTClient(self.mqtt_client_name, self.config, self.paths, [(self.mqtt_topic, 0)], self.mqtt_receive, self.loop)
        self.scan_task = None
        if self.source_type == 'provider':
            if self.the_function is not None:
                self.scan_task = self.loop.create_task(self.scanner())

    def stop(self):
        # for the moment not sure what to stop here
        logging.info('Shutting down DataSource: %s' % self.name)
        if self.source_type == 'provider':
            self.scan_task.cancel()
        self.mqtt_client.stop()

    async def scanner(self):
        # this is the scan loop
        while True:
            await self.update()
            await asyncio.sleep(self.scan_cycle)

    def mqtt_receive(self, topic, msg):
        """
        handle a mqtt message
        :param topic: mqtt topic
        :type topic: str
        :param msg: message
        :type msg: str
        """
        # TODO messageprocessor should take and return NSMessage objects only
        # logging.debug('received an mqtt messaage on topic: %s' % topic)
        try:
            # result is an NSMessage as json
            if topic == self.mqtt_topic:
                self.handle_message(msg)
        except Exception as ex:
            logging.error('Unexpected Exception while mqtt_receive: %s', ex)

    def handle_message(self, message):
        # handle messages on our topic
        try:
            message_dict = json.loads(message)
            # we only care about request, someone askkng for the current value
            if self.source_type == 'provider':
                if message_dict['message_type'] == 'request':
                    value_message = {
                        'message_type': 'current_value',
                        'value': self.value
                    }
                    self.mqtt_client.publish(self.mqtt_topic, json.dumps(value_message))
            elif self.source_type == 'consumer':
                if message_dict['message_type'] == 'new_value' or message_dict['message_type'] == 'current_value':
                    logging.debug('new value for data_source: %s' % self.name)
                    if self.value != message_dict['value']:
                        self.value = message_dict['value']
                        self.value_json = json.dumps(message_dict['value'])
                        if self.the_function is not None:
                            self.the_function(self.value)
        except Exception as ex:
            logging.exception('exception while handling data source message: %s' % ex)

    def get_value(self):
        return self.value

    async def update(self):
        # get the latest value using get_func and then advertize it if it changed
        if self.source_type == 'provider':
            # this check should not be unnecessary, as the scanner task is not created for consumer
            try:
                # logging.debug('updating data source: %s' % self.name)
                value = self.the_function()
                if value != '':
                    try:
                        value_json = json.dumps(value)
                    except json.JSONDecodeError:
                        logging.warning('JSONDecodeError while json encoding data source value, defaulting to empty string')
                        value_json = ''
                else:
                    value_json = ''
                if value_json != self.value_json:
                    # value changed
                    logging.debug('updating data source: %s' % self.name)
                    self.value = value
                    self.value_json = value_json
                    update_message = {
                        'message_type': 'new_value',
                        'value': value,
                    }
                    self.mqtt_client.publish(self.mqtt_topic, json.dumps(update_message))
            except Exception as ex:
                logging.exception('execeptions while updating a data_source named %s: %s' % (self.name, ex))
        else:
            logging.debug('Data Source with type: %s do not update' % self.source_type)
