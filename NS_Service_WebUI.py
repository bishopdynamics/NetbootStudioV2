#!/usr/bin/env python3
"""
Netboot Studio Service: Web UI
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2021 James Bishop (james@bishopdynamics.com)


import sys
import logging
import argparse
import ssl

from aiohttp import web
from NSLogger import get_logger
from NSService import NSService
from NSCommon import get_copyright


class NSWebUIService(NSService):
    """
    Netboot Studio Web UI Service. Provides a web-based interface for administering Netboot Studio
    """

    def __init__(self, args):
        """
        Web UI Service
        :param args:
        :type args:
        """
        super().__init__(args)
        logging.info('Netboot Studio Web UI Server v%s', self.version)
        self.webserver = NSWebUIserver(self.config, self.paths, self.version, self.loop)
        logging.info('Web UI Server is ready')
        self.start()


class NSWebUIserver:
    """
    A web server slightly tweaked to provide some const variables via /variables.js
    """
    # this just takes care of hosting web pages
    upload_chunk_size_mb = 16  # size of chunks used by file uploader, in MB. this MUST match the same value in NS_Service_API.py -> NSAPIServer
    app = None
    prerendered_files = {}
    resources = {}
    http_thread = None
    uploader_thread = None
    site = None

    def __init__(self, config, paths, version, loop):
        """
        WebUI Server
        :param config: config object
        :type config: RawConfigParser
        :param paths: paths object
        :type paths: dict
        :param version: version string
        :type version: str
        :param loop: asyncio loop
        :type loop: AbstractEventLoop
        """
        self.paths = paths
        self.loop = loop
        self.version = version
        self.host = '0.0.0.0'
        self.port = int(config.get('webserver', 'port'))
        self.copyright_string = get_copyright()
        self.upload_chunk_size = self.upload_chunk_size_mb * 1024 * 1024  # given as MB in config but need bytes
        # web_config stores static vars used to render webpages and resources
        self.web_config = {
            'webserver_port': config.get('webserver', 'port'),
            'broker_port': config.get('broker', 'port_websocket'),
            'broker_user': config.get('broker', 'user'),
            'broker_password': config.get('broker', 'password'),
            'apiserver_port': config.get('apiserver', 'port'),
            'upload_chunk_size': self.upload_chunk_size,
            'uploadserver_port': config.get('uploadserver', 'port'),
        }
        try:
            logging.info('Starting HTTPS Webserver on port %s' % self.port)
            self.app = web.Application(
                client_max_size=self.upload_chunk_size
            )
            self.app.add_routes([web.get('/', self.get_root)])
            self.app.add_routes([web.get('/variables.js', self.get_variables)])
            self.app.add_routes([web.static('/ipxe_builds/', self.paths['ipxe_builds'])])
            # TODO unfortunately this only works behind https when the client clock is correct, so stage server also serves this path
            self.app.add_routes([web.static('/boot_images/', self.paths['boot_images'])])
            self.app.add_routes([web.static('/', self.paths['web'])])
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_context.load_cert_chain(self.paths['ssl_cert'], self.paths['ssl_key'])
            self.runner = web.AppRunner(self.app, access_log=None)  # access_log can be set to logging.Logger instance, or None to mute logging
            self.loop.run_until_complete(self.runner.setup())
            self.site = web.TCPSite(self.runner, self.host, self.port, ssl_context=self.ssl_context)
            self.loop.run_until_complete(self.site.start())
        except Exception as ex:
            logging.error('Unexpected Exception while setting up Webserver: %s', ex)

    async def get_variables(self, request):
        """
        Get /variables.js, dynamically rendered const variables
        :param request: web request (ignored)
        :type request: web.Request
        :return: web response
        :rtype: web.Response
        """
        # variables.js holds dynamically generated variables
        content = '// *****************  Content below this line auto-generated  **************************\n'
        content += 'const _BROKER_PORT = %s;\n' % self.web_config['broker_port']
        content += 'const _BROKER_USER = "%s";\n' % self.web_config['broker_user']
        content += 'const _BROKER_PASSWORD = "%s";\n' % self.web_config['broker_password']
        content += 'const _COPYRIGHT_STRING = "%s";\n' % self.copyright_string
        content += 'const WEBSERVER_PORT = %s;\n' % self.web_config['webserver_port']
        content += 'const APISERVER_PORT = %s;\n' % self.web_config['apiserver_port']
        content += 'const UPLOADSERVER_PORT = %s;\n' % self.web_config['uploadserver_port']
        content += 'const WEBSERVER_UPLOAD_CHUNK_SIZE = %s;\n' % (self.web_config['upload_chunk_size'] - 1)  # remember web side needs chunk size to be 1 less than server side
        content += '// *****************  End auto-generated content  **************************\n\n'
        return web.Response(text=content, status=200, content_type='text/javascript')

    async def get_root(self, request):
        """
        Get / (aka root of webserver), always returns main.html
        :param request: web request (ignored)
        :type request: web.Request
        :return: web file response
        :rtype: web.FileResponse
        """
        logging.info('Getting WebUI Page')
        with open(self.paths['web'].joinpath('main.html')) as mainfile:
            content = mainfile.read()
        return web.Response(text=content, status=200, content_type='text/html')
        # return web.FileResponse(self.paths['web'].joinpath('main.html'))


if __name__ == "__main__":
    # this is the main entry point
    ARG_PARSER = argparse.ArgumentParser(description='Netboot Studio WebUI Server', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
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
    logger = get_logger(name=__name__,
                        level=LOG_LEVEL)
    assert sys.version_info >= (3, 8), "Script requires Python 3.8+."
    NS = NSWebUIService(ARGS)
