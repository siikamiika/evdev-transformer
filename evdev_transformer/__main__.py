import os
import time
import argparse

from .config import ConfigManager
from .hub import Hub
from . import log

# enough time to release the enter key when starting manually
time.sleep(1)

NAME = 'evdev_transformer'

# args
parser = argparse.ArgumentParser(description=NAME)
parser.add_argument('config', type=str,
                    help='JSON config file specifying devices and links')
parser.add_argument('--log', type=str, nargs='?',
                    help='Log level (CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET), '
                         'also available with the LOGLEVEL environment variable')
args = parser.parse_args()

# logging
log_level_name = args.log or os.environ.get('LOGLEVEL', 'WARNING')
log.init(NAME, log_level_name)

config_path = os.path.expanduser(f'~/.config/evdev_transformer/{args.config}.json')
config_manager = ConfigManager(config_path)
hub = Hub(config_manager)
hub.start()
