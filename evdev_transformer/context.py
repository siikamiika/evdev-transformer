import libevdev

from .system_events import InputDeviceMonitor
from .device import EvdevWrapper

class InputContext:
    def __init__(self):
        self._devices = []
        self._device_monitor = InputDeviceMonitor()

    def events(self):
        for action, udev_device, rule in self._device_monitor.events():
            if action == 'add':
                device = self._create_device(udev_device)
                self._devices.append((device, rule))
                yield 'add', device, rule
            elif action == 'remove':
                device = self._remove_device(udev_device, rule)
                if device:
                    yield 'remove', device, rule

    def add_monitored_attrs(self, attrs):
        self._device_monitor.add_monitored_attrs(attrs)

    def remove_monitored_attrs(self, attrs):
        self._device_monitor.remove_monitored_attrs(attrs)

    def has_pressed_keys(self, keys, attrs=None):
        if attrs is not None:
            for device, rule in self._devices:
                if rule == attrs and device.has_pressed_keys(keys):
                    return True
            return False
        else:
            if not isinstance(keys, set):
                keys = set(keys)
            combined = set()
            for device, _ in self._devices:
                combined |= device.get_pressed_keys()
            return len(keys) == len(combined & keys)

    def _create_device(self, udev_device):
        devname = udev_device.get('DEVNAME')
        fd = open(devname, 'rb')
        return EvdevWrapper(libevdev.Device(fd))

    def _remove_device(self, udev_device, rule):
        devname = udev_device.get('DEVNAME')
        for device, rule in self._devices:
            if device.get_fd_name() == devname:
                self._devices.remove((device, rule))
                device.release()
                return device
        return None
