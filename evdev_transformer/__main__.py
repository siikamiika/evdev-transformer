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
from .context import EvdevWrapper

config_manager = ConfigManager('example_config.json')
device_monitor = InputDeviceMonitor()
source_devices = []

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
        elif action == 'remove':
            for source_device, rule2 in source_devices:
                if rule == rule2:
                    # TODO release device (relevant when config reload is supported)
                    source_devices.remove((source_device, rule2))
                    break

threading.Thread(target=monitor_devices).start()

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
            matching_devices = config_manager.get_matching_linked_devices(obj, source_devices)
            print('matching_devices', obj, source_devices, matching_devices)
            destination = config_manager.get_matching_destination(obj)
            if isinstance(destination, UinputDestination):
                for matching_device in matching_devices:
                    # TODO fails with touchpad
                    threading.Thread(target=forward_to_uinput, args=(matching_device, [])).start()
    elif event['type'] == 'remove':
        if isinstance(obj, Link):
            pass

# print(json.dumps(config.to_dict(), indent=4))
# print(config._current_links)
# config.activate_next_link('Unholy Alliance')
# print(config._current_links)
# exit()

# context = InputContext()
# context.add_monitored_attrs(apple_magic_trackpad)

# def handle_device(device, rule):
#     devname = device.get_fd_name()
#     uinput_device = device.create_uinput_device()
#     for events in device.events():
#         print(deserialize_events(serialize_events(events)))
#         uinput_device.send_events(events)
#         # if random.randint(0, 100) == 100:
#         #     context.remove_monitored_attrs(logitech_k400)
#         # elif random.randint(0, 100) == 100:
#         #     context.add_monitored_attrs(logitech_k400)

# for action, device, rule in context.events():
#     print(action, device, rule)
#     if action == 'add':
#         threading.Thread(target=handle_device, args=(device, rule)).start()
#     elif action == 'remove':
#         pass
