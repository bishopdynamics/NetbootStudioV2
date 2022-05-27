#!/usr/bin/env python3
"""
Netboot Studio Library: Pub Sub Messaging
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2021 James Bishop (james@bishopdynamics.com)

import asyncio
import logging
import paho.mqtt.client as mqtt


class NSMQTTClient:
    # Listens on a given list of mqtt topics, returns messages to a callback(msg, topic)

    def __init__(self, name, config, paths, topics, callback, loop):
        self.name = name
        self.config = config
        self.paths = paths
        self.callback = callback
        self.loop = loop
        self.topics = topics
        try:
            self.host = self.config.get('main', 'netboot_server_hostname')
            self.port = int(self.config.get('broker', 'port'))
            self.username = self.config.get('broker', 'user')
            self.password = self.config.get('broker', 'password')
            logging.debug('Starting MQTT Client named: %s, broker: %s:%s' % (self.name, self.host, self.port))
            self.client = mqtt.Client(self.name)
            self.client.on_message = self.on_message
            self.client.username_pw_set(username=self.username, password=self.password)
            self.client.tls_set(self.paths['ssl_full_chain'])
            self.client.tls_insecure_set(False)
            self.client.on_connect = self.on_connect
            self.client.on_connect_fail = self.on_connect_fail
            self.client.connect(self.host, self.port)
            self.loop.run_until_complete(self.do_client())
        except Exception as ex:
            logging.error('Unexpected Exception while setting up MQTT Client: %s', ex)

    async def do_client(self):
        self.client.loop_start()
        await asyncio.sleep(0.01)

    def on_message(self, client, userdata, message):
        msg = str(message.payload.decode('utf-8'))
        topic = str(message.topic)
        self.callback(topic, msg)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.debug('MQTT Client named: %s, successfully connected to %s:%s' % (self.name, self.host, self.port))
            self.subscribe(self.topics)
        elif rc == 5:
            logging.error('MQTT Client failed to connect: Authentication Error')
        else:
            logging.error('MQTT Client failed to connect, rc: %s' % rc)

    def on_connect_fail(self):
        logging.error('MQTT Client named: %s, failed to connect to %s:%s' % (self.name, self.host, self.port))

    def publish(self, topic, payload):
        # publish a message on a topic
        self.client.publish(topic, payload)

    def subscribe(self, topics):
        logging.debug('subscribing to topics: %s' % topics)
        self.client.subscribe(topics)

    def stop(self):
        logging.info('shutting down MQTT Client...')
        self.client.loop_stop()
