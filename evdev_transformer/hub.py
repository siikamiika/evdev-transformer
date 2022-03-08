import threading
from typing import (
    List,
    Dict,
    Tuple,
    Iterable,
)
import functools

from .config import (
    ConfigManager,
    Source,
    EvdevUdevSource,
    EvdevUnixSocketSource,
    SourceGroup,
    Destination,
    UinputDestination,
    SubprocessDestination,
    HidGadgetDestination,
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
    HidGadgetDestinationDevice,
)
from .transform import (
    EventTransform,
)
from .ipc import IpcManager
from . import log

class Hub:
    def __init__(self, config_manager: ConfigManager):
        self._config_manager = config_manager
        self._device_monitor = InputDeviceMonitor()
        self._ipc_manager = IpcManager()
        self._source_devices: List[SourceDevice] = []
        self._link_destination_device_cache: List[Tuple[str, str, DestinationDevice]] = []
        self._activated_links: Dict[str, str] = {}
        self._source_device_destination_device_pairs: List[Tuple[SourceDevice, DestinationDevice]] = []
        self._lock = threading.Lock()

    def start(self):
        threading.Thread(target=self._monitor_devices).start()
        threading.Thread(target=self._monitor_config).start()
        threading.Thread(target=self._handle_ipc).start()

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
                    # update device config
                    matching_devices[-1].set_activators([
                        (
                            a,
                            functools.partial(
                                self._config_manager.activate_next_link,
                                source_group=link.source_group,
                                activator=a
                            )
                        )
                        for a in link.activators
                    ])
                    matching_devices[-1].set_transforms([EventTransform.from_config(t) for t in source.transforms])
                    # activate current link and clean up old
                    if source.name not in self._activated_links:
                        self._activated_links[source.name] = destination.name
                        destination_device = self._get_destination_device(source, destination, matching_devices[-1])
                        for src, dst in self._source_device_destination_device_pairs:
                            if src is matching_devices[-1]:
                                self._source_device_destination_device_pairs.remove((src, dst))
                                break
                        self._source_device_destination_device_pairs.append((matching_devices[-1], destination_device))
            for key in self._activated_links:
                if key not in seen_sources:
                    del self._activated_links[key]

    def _get_destination_device(
        self,
        source: Source,
        destination: Destination,
        source_device: SourceDevice,
    ) -> DestinationDevice:
        for source_name, destination_name, destination_device in self._link_destination_device_cache:
            # TODO invalidate cache when updating matching config
            if source_name == source.name and destination_name == destination.name:
                log.debug(f'loaded destination device from cache {destination_device}')
                return destination_device
        if isinstance(destination, UinputDestination):
            destination_device = UinputDestinationDevice.create(source_device)
        elif isinstance(destination, SubprocessDestination):
            destination_device = SubprocessDestinationDevice.create(source_device, {'command': destination.command})
        elif isinstance(destination, HidGadgetDestination):
            destination_device = HidGadgetDestinationDevice.create(source_device)
        else:
            raise NotImplementedError(f'Destination {destination} not implemented')
        self._link_destination_device_cache.append((source.name, destination.name, destination_device))
        log.debug(f'created destination device {destination_device}')
        return destination_device

    def _forward_events(self, source_device: SourceDevice):
        while True:
            destination_device = None
            with self._lock:
                for src, dst in self._source_device_destination_device_pairs:
                    if src is source_device:
                        destination_device = dst
                        break
            if destination_device is not None:
                log.info(f'forward {source_device} {destination_device}')
                # TODO transforms
                events_iter = iter(source_device.events())
                try:
                    first_events = next(events_iter)
                    destination_device.send_events(first_events)
                except StopIteration:
                    break
                for events in events_iter:
                    log.debug(f'forward events {events} from {source_device} to {destination_device}')
                    destination_device.send_events(events)

    def _monitor_devices(self):
        for action, udev_device, rule in self._device_monitor.events():
            log.info(f'{action} {udev_device} {rule}')
            if action == 'add':
                source_device = EvdevSourceDevice.from_udev(udev_device, rule)
                threading.Thread(target=self._forward_events, args=(source_device,)).start()
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
            log.info(f'{event}')
            obj = event['object']
            if event['type'] == 'add':
                if isinstance(obj, Source):
                    if isinstance(obj, EvdevUdevSource):
                        log.info(f'add monitored attributes {obj.identifier}')
                        self._device_monitor.add_monitored_attrs(obj.identifier)
                    elif isinstance(obj, EvdevUnixSocketSource):
                        log.info(f'TODO {obj}')
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
            # TODO stop existing thread
            threading.Thread(target=self._forward_events, args=(source_device,)).start()
            log.info(f'new ipc source device available {source_device}')
            self._source_devices.append(source_device)
            self._update_links()
        for events in self._ipc_manager.events():
            threading.Thread(target=_handle_events, args=(events,)).start()
