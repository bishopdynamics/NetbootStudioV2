
# straight-up ganked from here: https://github.com/herzog0/best_python_logger
# heavily modified

# TODO this has become less and less relevant, we should get rid of it and use a standard logger

import logging.handlers
import threading
import logging
import random
import fcntl
import gzip
import json
import time
import sys
import os
import io


_lock = threading.RLock()


def color_cheat_sheet():
    # This doesn't work very good in IDEs python consoles.
    terse = "-t" in sys.argv[1:] or "--terse" in sys.argv[1:]
    write = sys.stdout.write
    for i in range(2 if terse else 10):
        for j in range(30, 38):
            for k in range(40, 48):
                if terse:
                    write("\33[%d;%d;%dm%d;%d;%d\33[m " % (i, j, k, i, j, k))
                else:
                    write("%d;%d;%d: \33[%d;%d;%dm Hello, World! \33[m \n" %
                          (i, j, k, i, j, k,))
            write("\n")


class Colors:
    grey = "\x1b[0;37m"
    green = "\x1b[1;32m"
    yellow = "\x1b[1;33m"
    red = "\x1b[1;31m"
    purple = "\x1b[1;35m"
    blue = "\x1b[1;34m"
    light_blue = "\x1b[1;36m"
    reset = "\x1b[0m"
    blink_red = "\x1b[5m\x1b[1;31m"


class CustomFormatter(logging.Formatter):
    """Logging Formatter to add colors and count warning / errors"""
    def __init__(self, auto_colorized=True, custom_format: str = None):
        super(CustomFormatter, self).__init__()
        self.auto_colorized = auto_colorized
        self.custom_format = custom_format
        self.FORMATS = self.define_format()
        # if auto_colorized and custom_format:
        #     print("WARNING: Ignoring auto_colorized argument because you provided a custom_format")

    def define_format(self):
        # Levels
        # CRITICAL = 50
        # FATAL = CRITICAL
        # ERROR = 40
        # WARNING = 30
        # WARN = WARNING
        # INFO = 20
        # DEBUG = 10
        # NOTSET = 0

        if self.auto_colorized:

            format_prefix = f"{Colors.purple}%(asctime)s{Colors.reset} " \
                            f"{Colors.blue}%(name)s{Colors.reset} " \
                            f"{Colors.light_blue}(%(filename)s:%(lineno)d){Colors.reset} "

            format_suffix = "%(levelname)s - %(message)s"

            return {
                logging.DEBUG: format_prefix + Colors.blue + format_suffix + Colors.reset,
                logging.INFO: format_prefix + Colors.grey + format_suffix + Colors.reset,
                logging.WARNING: format_prefix + Colors.yellow + format_suffix + Colors.reset,
                logging.ERROR: format_prefix + Colors.red + format_suffix + Colors.reset,
                logging.CRITICAL: format_prefix + Colors.blink_red + format_suffix + Colors.reset
            }

        else:
            if self.custom_format:
                _format = self.custom_format
            else:
                _format = f"%(asctime)s %(threadName)s (%(filename)s:%(lineno)d) %(levelname)s - %(message)s"
            return {
                logging.DEBUG: _format,
                logging.INFO: _format,
                logging.WARNING: _format,
                logging.ERROR: _format,
                logging.CRITICAL: _format
            }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# Just import this function into your programs
# "from logger import get_logger"
# "logger = get_logger(__name__)"
# Use the variable __name__ so the logger will print the file's name also
class __NullHandler(io.StringIO):
    def emit(self, record):
        pass

    def write(self, *args, **kwargs):
        pass


class SpecialHandler(logging.StreamHandler):
    message_storage = None

    def __init__(self, msg_storage):
        self.message_storage = msg_storage
        logging.StreamHandler.__init__(self)

    def emit(self, record):
        l_text = self.format(record)  # MUST call this first, for all the attributes of record to be populated
        l_obj = {
            'asctime': record.asctime,
            'threadname': record.name,
            'filelocation': '(%s:%s)' % (record.filename, record.lineno),
            'level': record.levelname,
            'message': record.message}
        self.message_storage.append(l_obj)
        print(l_text)


def get_logger(name, auto_colorized=True, custom_format: str = None, level=logging.INFO, msg_storage=None):

    logging.basicConfig(level=level, stream=__NullHandler())
    root = logging.root

    if msg_storage is not None:
        ch = SpecialHandler(msg_storage)
        ch.setLevel(level)
        ch.setFormatter(CustomFormatter(auto_colorized, custom_format))
        root.addHandler(ch)
    else:
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(CustomFormatter(auto_colorized, custom_format))
        root.addHandler(ch)

    return logging.getLogger(name)
