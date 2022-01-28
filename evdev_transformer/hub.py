import threading

import libevdev

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

class Hub:
    def __init__(self, config_manager: ConfigManager):
        self._config_manager = config_manager
        self._device_monitor = InputDeviceMonitor()
        self._source_devices = []
        self._activated_links = {}

    def start(self):
        threading.Thread(target=self._monitor_devices).start()
        threading.Thread(target=self._monitor_config).start()

    def _update_links(self):
        seen_sources = set()
        for link, sources, destination in self._config_manager.get_current_links():
            # TODO other source types
            for source in [s for s in sources if isinstance(s, EvdevUdevSource)]:
                seen_sources.add(source.name)
                matching_devices = [d for d, r in self._source_devices if r == source.udev_properties]
                if not matching_devices:
                    if source.name in self._activated_links:
                        del self._activated_links[source.name]
                    continue
                if self._activated_links.get(source.name) not in [None, destination.name]:
                    del self._activated_links[source.name]
                    matching_devices[0].release()
                if source.name not in self._activated_links:
                    self._activated_links[source.name] = destination.name
                    # TODO transforms
                    # TODO other destination types
                    threading.Thread(target=self._forward_to_uinput, args=(matching_devices[0], [])).start()
        for key in self._activated_links:
            if key not in seen_sources:
                del self._activated_links[key]

    def _create_evdev_device(self, udev_device):
        devname = udev_device.get('DEVNAME')
        fd = open(devname, 'rb')
        return EvdevWrapper(libevdev.Device(fd))

    def _forward_to_uinput(self, source_device, transforms):
        print('forward_to_uinput', source_device._device.id, transforms)
        uinput_device = source_device.create_uinput_device()
        # TODO transforms
        for events in source_device.events():
            print(deserialize_events(serialize_events(events)))
            uinput_device.send_events(events)

    def _monitor_devices(self):
        for action, udev_device, rule in self._device_monitor.events():
            print(action, udev_device, rule)
            if action == 'add':
                self._source_devices.append((self._create_evdev_device(udev_device), rule))
                self._update_links()
            elif action == 'remove':
                for source_device, rule2 in self._source_devices:
                    if rule == rule2:
                        self._source_devices.remove((source_device, rule2))
                        self._update_links()
                        break

    def _monitor_config(self):
        for event in self._config_manager.events():
            print(event)
            obj = event['object']
            if event['type'] == 'add':
                if isinstance(obj, Source):
                    if isinstance(obj, EvdevUdevSource):
                        print('add monitored attributes', obj.udev_properties)
                        self._device_monitor.add_monitored_attrs(obj.udev_properties)
                    elif isinstance(obj, EvdevUnixSocketSource):
                        print('TODO', obj)
                elif isinstance(obj, SourceGroup):
                    pass
                elif isinstance(obj, Destination):
                    pass
                elif isinstance(obj, Link):
                    self._update_links()
            elif event['type'] == 'remove':
                if isinstance(obj, Link):
                    self._update_links()
