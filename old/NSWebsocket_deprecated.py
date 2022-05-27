#!/usr/bin/env python3
# Netboot Studio Websocket Server
#   wrapper around the python3 asyncio to provide callbacks

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020 James Bishop (james@bishopdynamics.com)

#   I initially really struggled with wrapping my head around asyncio implementation of
#   websockets library, as is built-in with python3.5+. I saw the same pattern copy/pasted
#   across many different sites, but I could never get it to work as described. Once I finally
#   got it working, I decided I never wanted to deal with asyncio again, so i wrapped it all
#   up in a class that behaves closer to the older python2.7 callback-style websocket libraries


import time
import logging
import asyncio
import ssl

from threading import Thread
import websockets

from NSCommon import NSSafeQueue


class NSWebsocket:
    # wraps asyncio websockets library into a simpler callback interface
    # pass port and receive handler to constructor
    # only two methods: send(msg), stop()
    # you dont really need to stop() since the thread is daemonized
    inbound_worker = None
    queue_ws_inbound = None
    queue_ws_outbound = None
    webocket_log_level = logging.INFO  # control logging level of websocket internals

    # TODO currently always sends to all reachable known clients

    def __init__(self, config, paths, receive_handler, loop):
        self.config = config
        self.paths = paths
        self.receive_handler = receive_handler
        self.loop = loop
        self.host = ''
        self.port = int(self.config.get('websocket', 'port'))
        self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.ssl_context.load_cert_chain(self.paths['ssl_cert'], self.paths['ssl_key'])
        self.clients = set()
        logging.info('Starting WSS Websocket Server on port %s', self.port)
        self.queue_ws_inbound = NSSafeQueue(loop=self.loop, maxsize=0)
        self.queue_ws_outbound = NSSafeQueue(loop=self.loop, maxsize=0)
        logging.getLogger('websockets.server').setLevel(self.webocket_log_level)
        logging.getLogger('websockets.protocol').setLevel(self.webocket_log_level)
        _ws_instance = websockets.serve(self._websocket_handler, host=self.host, port=self.port, loop=self.loop, ssl=self.ssl_context)
        self.loop.run_until_complete(_ws_instance)
        logging.debug('Starting worker thread to process inbound websocket message queue')
        self.inbound_worker = Thread(target=self._process_queue_inbound_ws)
        self.inbound_worker.setDaemon(True)
        self.inbound_worker.start()

    def stop(self):
        logging.info('shutting down Websocket Server')
        logging.debug('websocket shutdown does nothing at the moment')

    def _process_queue_inbound_ws(self):
        _queue = self.queue_ws_inbound
        while True:
            if _queue:
                while not _queue.empty():
                    try:
                        _item = _queue.get()
                        self._websocket_receive(_item)
                    except Exception:
                        logging.exception('Error while processing an inbound websocket message queue')
            time.sleep(0.01)  # lets the outbound task do something

    async def _websocket_handler(self, websocket, path):
        # this is the handler given to the websocket server to handle in/out
        try:
            outbound_task = asyncio.ensure_future(self._websocket_outbound_handler(websocket, path))
            inbound_task = asyncio.ensure_future(self._websocket_inbound_handler(websocket, path))
            done, pending = await asyncio.wait(
                [inbound_task, outbound_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.sleep(0)
        except Exception:
            logging.exception('Unexpected exception in websocket_handler')

    async def _websocket_inbound_handler(self, websocket, path):
        try:
            self.clients.add(websocket)  # clients is a set, so no duplicates will be allowed
            async for message in websocket:
                self.queue_ws_inbound.put(message)
        except:
            # dont particularly care about errors here, it means a client probably disconnected
            pass
        await asyncio.sleep(0)

    async def _websocket_outbound_handler(self, websocket, path):
        while True:
            while not self.queue_ws_outbound.empty():
                # note: all messages go to all clients, up to clients to filter by target
                # if a client has disconnected, they get removed from the list
                message = self.queue_ws_outbound.get()
                logging.debug('Sending websocket message')
                try:
                    _bad_clients = set()
                    for _this_client in self.clients:
                        try:
                            await _this_client.send(message)
                        except Exception as exa:
                            _bad_clients.add(_this_client)
                            logging.debug('removing websocket client that failed to send')
                            logging.debug('exception was: %s', exa)
                    for _this_client in _bad_clients:
                        try:
                            self.clients.remove(_this_client)
                        except Exception:
                            logging.exception('Unexpected exception while trying to remove a bad client from list')
                            pass
                except Exception:
                    logging.exception('Unexpected exception while trying to send ws msg to all clients')
                    pass
                await asyncio.sleep(0)
            await asyncio.sleep(0)  # lets the inbound task do something

    def _websocket_receive(self, msg):
        # Do something with a received message
        logging.debug('Received websocket message: %s', msg)
        self.receive_handler(msg)

    def send(self, msg):
        # queue message to be sent async later
        logging.debug('Queueing outbound websocket message')
        self.queue_ws_outbound.put(msg)
