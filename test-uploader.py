#!/usr/bin/env python3
# Test Uploader

# ignore rules:
#   docstring
#   too-broad-exception
#   line-too-long
#   too-many-branches
#   too-many-statements
#   too-many-public-methods
#   too-many-lines
#   too-many-nested-blocks
#   toddos (annotations linter handling this)
# pylint: disable=C0111,W0703,C0301,R0912,R0915,R0904,C0302,R1702,W0511

import sys
import logging
import pathlib
import asyncio
import tempfile
import ssl

from aiohttp import web
from aiohttp_tus import setup_tus
from aiohttp_middlewares import cors_middleware
from aiohttp_middlewares.cors import DEFAULT_ALLOW_HEADERS


class APIService:
    paths = {}  # all paths we need to track are stored here
    app = None
    http_thread = None
    site = None
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
    host = '0.0.0.0'
    port = 8085

    def __init__(self, _logger):
        self.logger = _logger
        self.paths['certs'] = pathlib.Path('./certs')
        self.paths['ssl_cert'] = self.paths['certs'].joinpath('server_cert.pem')  # SSL cert required for HTTPS and WSS
        self.paths['ssl_key'] = self.paths['certs'].joinpath('server_key.pem')  # SSL key required for HTTPS and WSS
        self.loop = asyncio.new_event_loop()
        self.upload_chunk_size = 16 * 1024 * 1024  # given as MB in config but need bytes
        with tempfile.TemporaryDirectory() as upload_temp:
            self.paths['upload_temp'] = pathlib.Path(upload_temp)
            try:
                logging.info('Starting HTTPS API Server on port %s' % self.port)
                self.app = web.Application(
                    client_max_size=self.upload_chunk_size,
                    middlewares=(
                        cors_middleware(
                            allow_all=True,
                            allow_methods=self.cors_allow_methods,
                            allow_headers=self.cors_allow_headers,
                            expose_headers=self.cors_expose_headers,
                            allow_credentials=True,
                        ),
                    )
                )
                logging.debug('temp_path used for uploads this session: %s' % self.paths['upload_temp'])
                self.tusapp = setup_tus(self.app, upload_path=self.paths['upload_temp'], upload_url='/upload', allow_overwrite_files=False)
                self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                self.ssl_context.load_cert_chain(self.paths['ssl_cert'], self.paths['ssl_key'])
                self.runner = web.AppRunner(self.app, access_log=self.logger)
                self.loop.run_until_complete(self.runner.setup())
                self.site = web.TCPSite(self.runner, self.host, self.port, ssl_context=self.ssl_context)
                self.loop.run_until_complete(self.site.start())
                logging.info('API Server is ready')
                self.loop.run_forever()
            except KeyboardInterrupt:
                pass
            except Exception as ex:
                logging.error('Unexpected Exception while setting up API Server: %s', ex)
            finally:
                logging.info('Shutting down API Server')
                self.loop.run_until_complete(self.site.stop())
                self.loop.run_until_complete(self.app.shutdown())
                self.loop.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    API_SRV = APIService(logging.getLogger(__name__))
