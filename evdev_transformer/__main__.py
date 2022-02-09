import sys
import time

from .config import ConfigManager
from .hub import Hub

# enough time to release the enter key when starting manually
time.sleep(1)

config_manager = ConfigManager(sys.argv[1])
hub = Hub(config_manager)
hub.start()
