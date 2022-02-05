import sys

from .config import ConfigManager
from .hub import Hub

config_manager = ConfigManager(sys.argv[1])
hub = Hub(config_manager)
hub.start()
