import pyudev

class InputDeviceMonitor:
    def __init__(self):
        self._monitored = []

    def add_monitored_attrs(self, attributes):
        if attributes not in self._monitored:
            self._monitored.append(attributes)

    def remove_monitored_attrs(self, attributes):
        if attributes in self._monitored:
            self._monitored.remove(attributes)

    def events(self):
        context = pyudev.Context()
        # first yield devices that already exist
        for device in context.list_devices(subsystem='input'):
            rule = self._get_matching_rule(device)
            if rule:
                yield 'add', device, rule
        # then monitor for changes
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem='input')
        for device in iter(monitor.poll, None):
            rule = self._get_matching_rule(device)
            if rule:
                yield device.get('ACTION'), device, rule

    def _get_matching_rule(self, device):
        for attributes in self._monitored:
            if (
                all(device.get(k) == v for k, v in attributes.items())
                and device.get('DEVNAME', '').startswith('/dev/input/event')
                and not device.get('DEVPATH', '').startswith('/devices/virtual/')
            ):
                return attributes
        return None
