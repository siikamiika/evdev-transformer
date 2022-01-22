import threading
import queue

import pyudev

class InputDeviceMonitor:
    def __init__(self):
        self._monitored = []
        self._event_queue = queue.Queue()

    def add_monitored_attrs(self, attributes):
        if attributes not in self._monitored:
            self._monitored.append(attributes)
            device = self._get_matching_device(attributes)
            if device:
                self._event_queue.put(('add', device, attributes))

    def remove_monitored_attrs(self, attributes):
        if attributes in self._monitored:
            self._monitored.remove(attributes)
            device = self._get_matching_device(attributes)
            if device:
                self._event_queue.put(('remove', device, attributes))

    def events(self):
        def _bg():
            for data in self._monitor():
                self._event_queue.put(data)
        threading.Thread(target=_bg).start()
        yield from iter(self._event_queue.get, None)

    def _monitor(self):
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem='input')
        for device in iter(monitor.poll, None):
            rule = self._get_matching_rule(device)
            if rule:
                yield device.get('ACTION'), device, rule

    def _get_matching_rule(self, device):
        for attributes in self._monitored:
            if self._is_rule_device_match(device, attributes):
                return attributes
        return None

    def _get_matching_device(self, rule):
        context = pyudev.Context()
        for device in context.list_devices(subsystem='input'):
            if self._is_rule_device_match(device, rule):
                return device
        return None

    def _is_rule_device_match(self, device, rule):
        return (
            all(device.get(k) == v for k, v in rule.items())
            and device.get('DEVNAME', '').startswith('/dev/input/event')
            and not device.get('DEVPATH', '').startswith('/devices/virtual/')
        )
