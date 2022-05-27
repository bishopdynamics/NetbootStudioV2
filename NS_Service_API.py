#!/usr/bin/env python3
"""
Netboot Studio Service: API Server
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2021 James Bishop (james@bishopdynamics.com)

import sys
import uuid
import ssl
import logging
import argparse

from datetime import datetime
from aiohttp import web

from aiohttp_middlewares import cors_middleware
from aiohttp_middlewares.cors import DEFAULT_ALLOW_HEADERS
from collections import OrderedDict

from NSPubSub import NSMQTTClient
from NSTaskManager import NSTaskManager
from NSCommon import NSSafeQueue, get_version, NSMessage
from NSMessageProcessor import NSMessageProcessor
from NSClientManager import NSClientManager
from NSLogger import get_logger
from NSService import NSService
from NSFileManager import NSFileManager
from NSDataSource import NSDataSource


class NSAPIService(NSService):
    """
    Netboot Studio API Service. Provides https auth endpoint, and api access via mqtt topic
    """
    mqtt_topics = [('api_request', 0), ]
    uploader = None

    def __init__(self, args):
        """
        API Service
        :param args: command-line arguments
        :type args: Namespace
        """
        super().__init__(args)
        logging.info('Netboot Studio API Server v%s', self.version)
        # TODO we can also add 'logs' here, and we can build our own log object to pass around and do our bidding
        self.data_sources = {
            'clients': self.ds_clients,
            'tasks': self.ds_tasks,
            'architectures': self.ds_architectures,
            'ipxe_commit_ids': self.ds_ipxe_commit_ids,
        }
        self.data_source_objects = dict()
        self.q_staging = NSSafeQueue(loop=self.loop, maxsize=self.queue_maxsize)
        self.client_manager = NSClientManager(self.config, self.paths, 'NSAPIService', self.loop)
        self.mqtt_client = NSMQTTClient(self.mqtt_client_name, self.config, self.paths, self.mqtt_topics, self.mqtt_receive, self.loop)
        self.file_manager = NSFileManager(self.config, self.paths, self.loop)
        self.msg_processor = NSMessageProcessor(self.config, self.paths, self.q_staging, self.client_manager, self.file_manager)
        self.apiserver = NSAPIServer(self.config, self.paths, self.msg_processor, self.client_manager, self.loop)
        self.task_manager = NSTaskManager(self.config, self.paths, self.q_staging, self.loop)
        self.stopabbles['mqtt_client'] = self.mqtt_client
        self.stopabbles['client_manager'] = self.client_manager
        self.setup_data_sources()
        logging.info('API Server is ready')
        self.start()

    def mqtt_receive(self, topic, msg):
        """
        Pass off the message to NSMessageProcessor, let it handle parsing it
        :param topic: mqtt topic
        :type topic: str
        :param msg: message
        :type msg: str
        """
        # TODO messageprocessor should take and return NSMessage objects only
        # logging.debug('received an mqtt messaage on topic: %s' % topic)
        try:
            # result is an NSMessage as json
            origin = 'broker'
            if topic == 'api_request':
                result = self.msg_processor.handle(msg, origin, topic=topic)
                result_message = NSMessage(result)
                topic = result_message.get('topic')
                self.mqtt_client.publish(topic, result)
        except Exception as ex:
            logging.error('Unexpected Exception while mqtt_receive: %s', ex)

    def setup_data_sources(self):
        logging.info('Setting up data sources')
        try:
            for source_name, source_func in self.data_sources.items():
                self.data_source_objects[source_name] = NSDataSource(self.config, self.paths, self.loop, source_name, 'provider', source_func)
        except Exception as ex:
            logging.exception('failed to setup_data_sources: %s' % ex)

    def ds_clients(self):
        return self.client_manager.get_clients()

    def ds_tasks(self):
        return self.task_manager.get_tasks()

    def ds_architectures(self):
        value = [
                    {
                        'name': 'amd64',
                        'description': '64-bit x86',
                    },
                    {
                        'name': 'arm64',
                        'description': '64-bit ARM',
                    }
                ]
        return value

    def ds_ipxe_commit_ids(self):
        # TODO actually fetch this data from the git repo, but we want to do it on a much longer loop like every 4 hours
        value = [
                    {
                        'commit_id': 'f24a279',
                        'name': 'Latest Commit (Oct 28, 2021)',
                    },
                    {
                        'commit_id': 'e6f9054',
                        'name': 'Last Stable (Oct 20, 2020)',
                    },
                    {
                        'commit_id': '988d2c1',
                        'name': 'Latest Tag 1.21.1 (Dec 31, 2020)',
                    },
                    {
                        'commit_id': '8f1514a',
                        'name': 'Next Latest Tag 1.20.1 (Jan 2, 2020)',
                    },
                    {
                        'commit_id': '13a6d17',
                        'name': 'Previous one we marked stable in old netbootstudio (Nov 29, 2020)',
                    },
                    {
                        'commit_id': '53e9fb5',
                        'name': 'Very old Tag v 1.0.0 (Feb 2, 2010)',
                    },
                ]
        return value


class NSAPIServer:
    """
    The API Server. Handles API calls only, it does not serve any pages or resources
    """
    upload_chunk_size_mb = 16  # size of chunks used by file uploader, in MB. this MUST match the same value in NS_Service_WebUI.py -> NSWebUIserver
    auth_ttl = 1800  # seconds, 30m = 1800; how long auth tokens are valid
    app = None
    auth_token_list = None
    site = None
    runner = None
    ssl_context = None
    uploader_apps = OrderedDict({})  # tus uploader apps will be stored in a dict here
    cors_allow_methods = ('GET', 'POST' 'PUT', 'PATCH', 'HEAD', 'OPTIONS')
    cors_allow_headers = DEFAULT_ALLOW_HEADERS + (
        "auth_token",
        "Authorization",
        "X-Requested-With",
        "X-Request-ID",
        "X-HTTP-Method-Override",
        "Tus-Resumable",
        "Upload-Length",
        "Upload-Offset",
        "Upload-Metadata",
        "Upload-Defer-Length",
        "Upload-Concat",
        "User-Agent",
        "Referrer",
        "Origin",
        "Content-Type",
        "Content-Length",
        "Location",
    )
    cors_expose_headers = (
        "Location",
        "X-Requested-With",
        "X-Request-ID",
        "X-HTTP-Method-Override",
        "Content-Type",
        "Tus-Version",
        "Tus-Resumable",
        "Tus-Max-Size",
        "Tus-Extension",
        "Upload-Metadata",
        "Upload-Defer-Length",
        "Upload-Concat",
        "Upload-Offset",
        "Upload-Length",
    )

    def __init__(self, config, paths, msg_processor, client_mgr, loop):
        """
        API Server
        :param config: config object
        :type config: RawConfigParser
        :param paths: paths dictionary
        :type paths: dict
        :param msg_processor: message processor
        :type msg_processor: NSMessageProcessor
        :param client_mgr: client manager
        :type client_mgr: NSClientManager
        :param loop: asyncio loop
        :type loop: AbstractEventLoop
        """
        self.paths = paths
        self.msg_processor = msg_processor
        self.client_manager = client_mgr
        self.loop = loop
        self.auth_token_list = dict()
        self.version = get_version(self.paths['program_base'])
        self.host = '0.0.0.0'
        self.port = int(config.get('apiserver', 'port'))
        self.admin_user = config.get('apiserver', 'admin_user')
        self.admin_password = config.get('apiserver', 'admin_password')
        self.upload_chunk_size = self.upload_chunk_size_mb * 1024 * 1024  # given as MB in config but need bytes
        try:
            logging.info('Starting HTTPS API Server on port %s' % self.port)
            self.app = web.Application(
                client_max_size=self.upload_chunk_size,
                middlewares=[
                    cors_middleware(
                        allow_all=True,
                        allow_methods=self.cors_allow_methods,
                        allow_headers=self.cors_allow_headers,
                        expose_headers=self.cors_expose_headers,
                        allow_credentials=True,
                    ),
                ]
            )
            self.setup_routes()
            self.setup_ssl_context()
            self.setup_web_runner()
            self.loop.run_until_complete(self.site.start())
        except Exception as ex:
            logging.error('Unexpected Exception while setting up API Server: %s', ex)

    def setup_routes(self):
        """
        Setup webserver routes
        """
        self.app.add_routes([web.post('/auth', self.post_auth)])

    def setup_ssl_context(self):
        """
        Setup SSL Context
        """
        self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.ssl_context.load_cert_chain(self.paths['ssl_cert'], self.paths['ssl_key'])

    def setup_web_runner(self):
        """
        Setup web runner
        """
        self.runner = web.AppRunner(self.app, access_log=None)  # access_log can be set to logging.Logger instance, or None to mute logging
        self.loop.run_until_complete(self.runner.setup())
        self.site = web.TCPSite(self.runner, self.host, self.port, ssl_context=self.ssl_context)

    async def post_auth(self, request):
        """
        Handle requests to the '/auth' endpoint (POST only), for handing out and validating auth tokens
        :param request: request object
        :type request:
        :return: response object
        :rtype:
        """
        # TODO this auth mechanism is just a placeholder
        request_data = await request.json()
        client_ipaddress = request.remote
        if 'user' in request_data and 'password' in request_data:
            # user login request
            if request_data['user'] == self.admin_user:
                if request_data['password'] == self.admin_password:
                    new_token = await self.generate_auth_token()
                    response_content = '{"auth_token": "%s"}' % new_token
                    logging.info('Successful login request from client: %s' % client_ipaddress)
                    return web.Response(text=response_content, status=200, content_type='text/json')
        elif 'auth_token' in request_data:
            # renew token request
            is_valid = await self.validate_auth_token(request_data['auth_token'])
            if is_valid:
                new_token = await self.generate_auth_token()
                response_content = '{"auth_token": "%s"}' % new_token
                logging.info('Successfully renewed token for client: %s' % client_ipaddress)
                return web.Response(text=response_content, status=200, content_type='text/json')
        # if we got here, auth failed
        response_content = '{"auth_token": ""}'
        logging.debug('Refused token renew request from: %s' % client_ipaddress)
        return web.Response(text=response_content, status=200)

    async def generate_auth_token(self):
        """
        Generate an auth token
        :return: auth token
        :rtype: str
        """
        # tokens are simple uuid4 strings, no fancy stuff
        # we track them in a dict along with a timestamp, and remove any older than auth_ttl
        _token = '%s' % uuid.uuid4()
        _time_now = datetime.timestamp(datetime.now())
        self.auth_token_list[_token] = dict()
        self.auth_token_list[_token]['timestamp'] = _time_now
        _delete_list = list()
        for this_token in self.auth_token_list:
            this_timestamp = self.auth_token_list[this_token]['timestamp']
            this_token_age = _time_now - this_timestamp
            if this_token_age > self.auth_ttl:
                logging.debug('marking an expired token for deletion, %s seconds old' % this_token_age)
                _delete_list.append(this_token)
        for this_token in _delete_list:
            logging.debug('deleting expired token: %s' % this_token)
            del self.auth_token_list[this_token]
        return _token

    async def validate_auth_token(self, token):
        """
        Check if auth_token is in our list, and not expired
        :param token: auth token
        :type token: str
        :return: valid
        :rtype: bool
        """
        #
        if token in self.auth_token_list:
            _time_now = datetime.timestamp(datetime.now())
            this_timestamp = self.auth_token_list[token]['timestamp']
            this_token_age = _time_now - this_timestamp
            if this_token_age > self.auth_ttl:
                logging.debug('Refusing expired token age: %s seconds' % this_token_age)
                del self.auth_token_list[token]
                return False
        else:
            logging.debug('Refusing invalid token')
            return False
        return True


if __name__ == "__main__":
    # this is the main entry point
    ARG_PARSER = argparse.ArgumentParser(description='Netboot Studio API Server', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ARG_PARSER.add_argument('-m', dest='mode', action='store',
                            type=str, default='prod', choices=['prod', 'dev'],
                            help='which mode to run in')
    ARG_PARSER.add_argument('-c', dest='configdir', action='store',
                            type=str, default='/opt/NetbootStudio',
                            help='path to config folder')
    ARGS = ARG_PARSER.parse_args()
    if ARGS.mode == 'dev':
        # dev mode has info logging, but with lots of extra internal info at each log
        LOG_LEVEL = logging.DEBUG
    else:
        LOG_LEVEL = logging.INFO
    # courtesy of NSLogger
    logger = get_logger(name=__name__,
                        level=LOG_LEVEL)
    assert sys.version_info >= (3, 8), "Script requires Python 3.8+."
    NS = NSAPIService(ARGS)
