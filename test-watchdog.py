#!/usr/bin/env python3
"""
Netboot Studio File Manager
"""

#    This file is part of Netboot Studio, a system for managing netboot clients
#    Copyright (C) 2020-2023 James Bishop (james@bishopdynamics.com)

import asyncio
import pathlib
import logging
import yaml
import json
import time

from threading import Thread
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler





def on_created(event):
    print(f"hey, {event.src_path} has been created!")


def on_deleted(event):
    print(f"what the f**k! Someone deleted {event.src_path}!")


def on_modified(event):
    print(f"hey buddy, {event.src_path} has been modified")


# def on_moved(event):
#     print(f"ok ok ok, someone moved {event.src_path} to {event.dest_path}")


my_event_handler = PatternMatchingEventHandler(patterns=['*.ipxe'], ignore_patterns=None, ignore_directories=True, case_sensitive=False)
my_event_handler.on_created = on_created
my_event_handler.on_deleted = on_deleted
my_event_handler.on_modified = on_modified
# my_event_handler.on_moved = on_moved

my_observer = Observer()
my_observer.schedule(event_handler=my_event_handler, path=str(pathlib.Path('./tmp')), recursive=False)

my_observer.start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    my_observer.stop()
    my_observer.join()
