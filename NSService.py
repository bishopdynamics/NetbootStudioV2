#!/usr/bin/env python3
"""
Netboot Studio Service Base Class
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2021 James Bishop (james@bishopdynamics.com)


import sys
import uuid
import time
import signal
import asyncio
import logging
import datetime

from configparser import RawConfigParser

from collections import OrderedDict
from NSCommon import get_version, build_paths, check_config
from NSClientManager import NSClientManager


class NSService:
    paths = {}  # all paths we need to track are stored here
    queue_maxsize = 0  # how large to allow a queue to get, affects all queues, 0 = infinite
    stopabbles = OrderedDict({})  # store things here that have .stop() methods, and we will call them on cleanup
    loop = None  # asyncio loop
    config = RawConfigParser()
    stopping = False

    def __init__(self, args):
        try:
            self.start_time = datetime.datetime.now()
            self.paths = build_paths(args.configdir)
            self.version = get_version(self.paths['program_base'])
            check_config(self.paths)
            self.config.read(self.paths['config.ini'])
            self.mqtt_client_name = 'NSService-%s' % uuid.uuid4()
            self.loop = asyncio.new_event_loop()

        except Exception as ex:
            logging.exception('exception while performing base class init for NSService: %s', ex)
            sys.exit(1)

    def start(self):
        try:
            signal.signal(signal.SIGTERM, self.handle_signal)
            signal.signal(signal.SIGINT, self.handle_signal)
            self.loop.run_until_complete(asyncio.sleep(0.1))
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        except Exception as ex:
            logging.error('Unexpected Exception while setting up API Server: %s', ex)
        finally:
            self.loop.close()

    def stop(self):
        # clean things up
        if self.stopping:
            logging.debug('NSService.stop() was already called')
        else:
            self.stopping = True
            try:
                for thingname, thingobj in self.stopabbles.items():
                    logging.debug('stopping %s' % thingname)
                    thingobj.stop()
                logging.debug('cancelling asyncio tasks')
                for task in asyncio.all_tasks(loop=self.loop):
                    task.cancel()
                logging.debug('stopping event loop')
                self.loop.stop()
            except Exception as ex:
                logging.exception('exception while cleaning up: %s' % ex)
                pass

    def handle_signal(self, this_signal, this_frame=None):
        """
        Handle signal from system and cleanup (sigterm, sigint)
        :param this_signal: signal
        :type this_signal: int
        :param this_frame:
        :type this_frame:
        """
        try:
            logging.info('Caught signal, shutting down')
            logging.debug('Caught signal: %s', this_signal)
            self.stop()
            sys.exit(0)
        except Exception as ex:
            logging.error('Unexpected Exception while handling signal: %s', ex)
            sys.exit(1)
