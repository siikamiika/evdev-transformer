from .config import ConfigManager
from .hub import Hub

config_manager = ConfigManager('example_config.json')
hub = Hub(config_manager)
hub.start()
