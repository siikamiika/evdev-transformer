import threading
import random
import json

import libevdev

from .context import InputContext
from .serde import (
    serialize_events,
    deserialize_events
)
from .config import (
    ConfigManager,
    Source,
    EvdevUdevSource,
    EvdevUnixSocketSource,
    SourceGroup,
    Destination,
    UinputDestination,
    Activator,
    Link,
)
from .system_events import InputDeviceMonitor
from .device import EvdevWrapper

config_manager = ConfigManager('example_config.json')
device_monitor = InputDeviceMonitor()
source_devices = []
activated_links = {}

def update_links():
    for link, sources, destination in config_manager.get_current_links():
        # TODO other source types
        for source in [s for s in sources if isinstance(s, EvdevUdevSource)]:
            if source.name not in activated_links:
                matching_devices = [d for d, r in source_devices if r == source.udev_properties]
                if matching_devices:
                    source_device = matching_devices[0]
                    activated_links[source.name] = destination.name
                    # TODO transforms
                    # TODO other destination types
                    threading.Thread(target=forward_to_uinput, args=(source_device, [])).start()

def create_evdev_device(udev_device):
    devname = udev_device.get('DEVNAME')
    fd = open(devname, 'rb')
    return EvdevWrapper(libevdev.Device(fd))

def forward_to_uinput(source_device, transforms):
    print('forward_to_uinput', source_device._device.id, transforms)
    uinput_device = source_device.create_uinput_device()
    # TODO transforms
    for events in source_device.events():
        print(deserialize_events(serialize_events(events)))
        uinput_device.send_events(events)

def monitor_devices():
    for action, udev_device, rule in device_monitor.events():
        print(action, udev_device, rule)
        if action == 'add':
            source_devices.append((create_evdev_device(udev_device), rule))
            update_links()
        elif action == 'remove':
            for source_device, rule2 in source_devices:
                if rule == rule2:
                    # TODO release device (relevant when config reload is supported)
                    source_devices.remove((source_device, rule2))
                    break

def monitor_config():
    for event in config_manager.events():
        print(event)
        obj = event['object']
        if event['type'] == 'add':
            if isinstance(obj, Source):
                if isinstance(obj, EvdevUdevSource):
                    print('add monitored attributes', obj.udev_properties)
                    device_monitor.add_monitored_attrs(obj.udev_properties)
                elif isinstance(obj, EvdevUnixSocketSource):
                    print('TODO', obj)
            elif isinstance(obj, SourceGroup):
                pass
            elif isinstance(obj, Destination):
                pass
            elif isinstance(obj, Link):
                update_links()
        elif event['type'] == 'remove':
            if isinstance(obj, Link):
                pass

threading.Thread(target=monitor_devices).start()
threading.Thread(target=monitor_config).start()
