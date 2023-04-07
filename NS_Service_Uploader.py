#!/usr/bin/env python3
"""
Netboot Studio Service: File Upload Server
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2023 James Bishop (james@bishopdynamics.com)

# A note from Bishop, Feb 5, 2021
#
# I hate CORS, but even more than that, I hate that modern browsers cannot facilitate file uploads larger than 1GB. Thats stupid.
# I've been fighting with this file uploader solution (uploading files multi-part to get around file size restrictions is hard),
# for days, trying to get it to work nicely with CORS since my webserver and api server are on separate ports,
# and it stubbornly refused to behave as documented.
# It turns out, there's a setting on the javascript side removeFingerprintOnSuccess: false, which was screwing me over.
# If the fingerprint is left behind (its a cookie), then the next time you try to upload a file with the same name,
# it will cause the server to respond without any CORS headers, and everything will shit the bed.
# i've been sitting here testing with the same file over-and-over, tweaking settings on the server-side,
# trying to figure out why CORS was so pissed off, when in reality it was a stupid client-side cookie causing all my problems
#
# so for future reference, this is how you implement the javascript side of this correctly:
# <script>
#
# URL_APISERVER = 'https://' + SERVER_HOSTNAME + ':' + APISERVER_PORT;
#
# function SetupUploader(){
# 	try {
# 		var uppy = Uppy.Core({
# 		  id: 'uppy',
# 		  autoProceed: true,
# 		  allowMultipleUploads: true,
# 		  debug: false,
# 		  restrictions: {
# 		    maxFileSize: null,
# 		    minFileSize: null,
# 		    maxTotalFileSize: null,
# 		    maxNumberOfFiles: null,
# 		    minNumberOfFiles: null,
# 		    allowedFileTypes: null
# 		  },
# 		  infoTimeout: 5000
# 		});
# 		uppy.use(Uppy.DragDrop, { target: '#file-upload-drop'});
# 		uppy.use(Uppy.Tus, {
# 			endpoint: URL_APISERVER + "/upload", chunkSize: WEBSERVER_UPLOAD_CHUNK_SIZE,
# 			headers: {
# 				'auth_token': GetAuthTokenFromSessionStorage(),
# 			},
# 			overridePatchMethod: false,
# 			resume: true,
#   			retryDelays: [0, 1000, 3000, 5000],
#   			removeFingerprintOnSuccess: true, // this is critical, or the next time you try to upload a file of the same name, it will get a completely unhelpful CORS error. FUCK CORS.
# 		});
# 		uppy.on('complete', function(result){
# 			UploadComplete(result);
# 		});
# 		uppy.on('upload-progress', function(file, progress){
# 			UploadProgress(file, progress);
# 		});
# 	} catch(e) {
# 		console.error('Exception while setting up uploader: ' + e);
# 	}
# }
#
# </script>


import shutil
import pathlib
import sys
import ssl
import logging
import argparse

from aiohttp import web
from aiohttp_tus import setup_tus
from aiohttp_middlewares import cors_middleware
from aiohttp_middlewares.cors import DEFAULT_ALLOW_HEADERS
from collections import OrderedDict

from NSPubSub import NSMQTTClient
from NSCommon import get_version
from NSLogger import get_logger
from NSService import NSService


# TODO kept the mqtt client for future use

class NSUploadService(NSService):
    """
    Netboot Studio Upload Service. Provides endpoints for uploading files
    """
    mqtt_topics = [('upload', 0), ]
    uploader = None

    def __init__(self, args):
        """
        Upload Service
        :param args: command-line arguments
        :type args: Namespace
        """
        super().__init__(args)
        logging.info('Netboot Studio Upload Server v%s', self.version)
        self.mqtt_client = NSMQTTClient(self.mqtt_client_name, self.config, self.paths, self.mqtt_topics, self.mqtt_receive, self.loop)
        self.uploader = NSUploadServer(self.config, self.paths, self.loop)
        self.stopabbles['mqtt_client'] = self.mqtt_client
        self.stopabbles['file_uploader'] = self.uploader
        logging.info('Upload Server is ready')
        self.start()

    def mqtt_receive(self, topic, msg):
        """
        Handle a message received by mqtt client
        :param topic: mqtt topic
        :type topic: str
        :param msg: message
        :type msg: str
        """
        try:
            # origin = 'broker'
            if topic == 'upload':
                logging.info('received a message on the upload topic: %s' % msg)
        except Exception as ex:
            logging.error('Unexpected Exception while mqtt_receive: %s', ex)


class NSUploadServer:
    """
    The Upload Server. File Uploads only, it does not serve any pages or resources
    """
    upload_chunk_size_mb = 16  # size of chunks used by file uploader, in MB. this MUST match the same value in NS_Service_WebUI.py -> NSWebUIserver
    app = None
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
    allowed_upload_destinations = ['certs', 'ipxe_builds', 'stage1_files', 'iso', 'packages', 'stage4', 'tftp_root', 'uboot_scripts', 'unattended_configs']

    def __init__(self, config, paths, loop):
        """
        Upload Server
        :param config: config object
        :type config: RawConfigParser
        :param paths: paths dictionary
        :type paths: dict
        """
        self.paths = paths
        self.version = get_version(self.paths['program_base'])
        self.host = '0.0.0.0'
        self.loop = loop
        self.port = int(config.get('uploadserver', 'port'))
        self.upload_chunk_size = self.upload_chunk_size_mb * 1024 * 1024  # given as MB in config but need bytes
        try:
            logging.info('Starting HTTPS Upload Server on port %s' % self.port)
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
            # TODO tus is not doing anything with auth_token being sent in header
            for destination in self.allowed_upload_destinations:
                logging.debug('starting upload handler for /upload_%s' % destination)
                self.uploader_apps[destination] = setup_tus(self.app, upload_path=self.paths[destination], upload_url='/upload_%s' % destination, allow_overwrite_files=False)
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_context.load_cert_chain(self.paths['ssl_cert'], self.paths['ssl_key'])
            self.runner = web.AppRunner(self.app, access_log=None)  # access_log can be set to logging.Logger instance, or None to mute logging
            self.loop.run_until_complete(self.runner.setup())
            self.site = web.TCPSite(self.runner, self.host, self.port, ssl_context=self.ssl_context)
            self.loop.run_until_complete(self.site.start())
        except Exception as ex:
            logging.error('Unexpected Exception while setting up Upload Server: %s', ex)

    def stop(self):
        # need to clean up those pesky .metadata and .resources folders
        logging.debug('cleaning up any leftover .metadata and .resources folders in each upload destination')
        for destination in self.allowed_upload_destinations:
            try:
                dest_path = pathlib.Path(self.paths[destination])
                pesky_meta = dest_path.joinpath('.metadata')
                pesky_res = dest_path.joinpath('.resources')
                if pesky_meta.is_dir():
                    shutil.rmtree(pesky_meta)
                if pesky_res.is_dir():
                    shutil.rmtree(pesky_res)
            except Exception as ex:
                logging.exception('exception while cleaning up destination: %s, ex: %s' % (destination, ex))


if __name__ == "__main__":
    # this is the main entry point
    ARG_PARSER = argparse.ArgumentParser(description='Netboot Studio Upload Server', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
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
    NS = NSUploadService(ARGS)
