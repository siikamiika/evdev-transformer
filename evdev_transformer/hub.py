import threading
from typing import (
    List,
    Dict,
    Tuple,
    Iterable,
)
import time

import libevdev

from .config import (
    ConfigManager,
    Source,
    EvdevUdevSource,
    EvdevUnixSocketSource,
    SourceGroup,
    Destination,
    UinputDestination,
    SubprocessDestination,
    Activator,
    Link,
)
from .system_events import InputDeviceMonitor
from .device import (
    SourceDevice,
    EvdevSourceDevice,
    UnixSocketSourceDevice,
    DestinationDevice,
    UinputDestinationDevice,
    SubprocessDestinationDevice,
)
from .ipc import IpcManager

class Hub:
    def __init__(self, config_manager: ConfigManager):
        self._config_manager = config_manager
        self._device_monitor = InputDeviceMonitor()
        self._ipc_manager = IpcManager()
        self._source_devices: List[SourceDevice] = []
        self._link_destination_device_cache: List[Tuple[str, str, DestinationDevice]] = []
        self._activated_links: Dict[str, str] = {}
        self._lock = threading.Lock()

    def start(self):
        threading.Thread(target=self._monitor_devices).start()
        threading.Thread(target=self._monitor_config).start()
        threading.Thread(target=self._handle_ipc).start()
        # def _test_cycle_links_periodic():
        #     while True:
        #         time.sleep(5)
        #         self._config_manager.activate_next_link('Unholy Alliance')
        # threading.Thread(target=_test_cycle_links_periodic).start()

    def _update_links(self):
        with self._lock:
            seen_sources = set()
            for link, sources, destination in self._config_manager.get_current_links():
                for source in sources:
                    seen_sources.add(source.name)
                    matching_devices = [d for d in self._source_devices if d.identifier == source.identifier]
                    if not matching_devices:
                        if source.name in self._activated_links:
                            del self._activated_links[source.name]
                        continue
                    if self._activated_links.get(source.name) not in [None, destination.name]:
                        del self._activated_links[source.name]
                        matching_devices[-1].release()
                    if len(matching_devices) > 1:
                        for extra_device in matching_devices[:-1]:
                            # TODO this can still leak memory
                            extra_device.release()
                            self._source_devices.remove(extra_device)
                        if source.name in self._activated_links:
                            del self._activated_links[source.name]
                    if source.name not in self._activated_links:
                        self._activated_links[source.name] = destination.name
                        destination_device = self._get_destination_device(source, destination, matching_devices[-1])
                        # TODO transforms
                        threading.Thread(
                            target=self._forward_events,
                            args=(matching_devices[-1], destination_device, [])
                        ).start()
            for key in self._activated_links:
                if key not in seen_sources:
                    del self._activated_links[key]

    def _get_destination_device(
        self,
        source: Source,
        destination: Destination,
        source_device: SourceDevice,
    ) -> DestinationDevice:
        print('get destination device')
        for source_name, destination_name, destination_device in self._link_destination_device_cache:
            # TODO invalidate cache when updating matching config
            if source_name == source.name and destination_name == destination.name:
                return destination_device
        # TODO other destination types
        if isinstance(destination, UinputDestination):
            destination_device = UinputDestinationDevice.create(source_device)
        elif isinstance(destination, SubprocessDestination):
            destination_device = SubprocessDestinationDevice.create(source_device, {'command': destination.command})
        else:
            raise NotImplementedError(f'Destination {destination} not implemented')
        self._link_destination_device_cache.append((source.name, destination.name, destination_device))
        return destination_device

    def _forward_events(
        self,
        source_device: SourceDevice,
        destination_device: DestinationDevice,
        transforms,
    ):
        print('forward', source_device, destination_device, transforms)
        # TODO transforms
        for events in source_device.events():
            destination_device.send_events(events)

    def _monitor_devices(self):
        for action, udev_device, rule in self._device_monitor.events():
            print(action, udev_device, rule)
            if action == 'add':
                source_device = EvdevSourceDevice.from_udev(udev_device, rule)
                self._source_devices.append(source_device)
                self._update_links()
            elif action == 'remove':
                for source_device in self._source_devices:
                    if source_device.identifier == rule:
                        self._source_devices.remove(source_device)
                        self._update_links()
                        break

    def _monitor_config(self):
        for event in self._config_manager.events():
            print(event)
            obj = event['object']
            if event['type'] == 'add':
                if isinstance(obj, Source):
                    if isinstance(obj, EvdevUdevSource):
                        print('add monitored attributes', obj.identifier)
                        self._device_monitor.add_monitored_attrs(obj.identifier)
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

    def _handle_ipc(self):
        # TODO thread safe
        def _handle_events(events: Iterable[Dict]):
            events_iter = iter(events)
            first_event = next(events_iter)
            # TODO filter based on config
            source_device = UnixSocketSourceDevice.from_ipc(first_event, events_iter)
            self._source_devices.append(source_device)
            self._update_links()
        for events in self._ipc_manager.events():
            threading.Thread(target=_handle_events, args=(events,)).start()
