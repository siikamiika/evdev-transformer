import pyudev
import threading

class InputDeviceMonitor:
    def __init__(self):
        self._monitored = []

    def add_monitored_attrs(self, attributes):
        self._monitored.append(attributes)

    def start(self, add_handler, remove_handler):
        def _bg():
            for device in self._monitor():
                action = device.get('ACTION')
                if action == 'add':
                    add_handler(device)
                elif action == 'remove':
                    remove_handler(device)
                elif action is None:
                    # already exists
                    add_handler(device)
        threading.Thread(target=_bg).start()

    def _monitor(self):
        context = pyudev.Context()
        # first yield devices that already exist
        for device in context.list_devices(subsystem='input'):
            if self._is_match(device):
                yield device
        # then monitor for changes
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem='input')
        for device in iter(monitor.poll, None):
            if self._is_match(device):
                yield device

    def _is_match(self, device):
        # TODO exclude uinput
        for attributes in self._monitored:
            if (
                all(device.get(k) == v for k, v in attributes.items())
                and all(device.get(k) for k in ['DEVNAME', 'MAJOR', 'MINOR'])
                and device.get('DEVNAME').startswith('/dev/input/event')
            ):
                return True
        return False
