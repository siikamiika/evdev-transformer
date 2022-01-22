import libevdev

from .system_events import InputDeviceMonitor

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
        libevdev_device = libevdev.Device(fd)
        libevdev_device.grab()
        return EvdevWrapper(libevdev_device)

    def _remove_device(self, udev_device, rule):
        devname = udev_device.get('DEVNAME')
        for device, rule in self._devices:
            if device.get_fd_name() == devname:
                self._devices.remove((device, rule))
                return device
        return None

class EvdevWrapper:
    def __init__(self, libevdev_device):
        self._device = libevdev_device
        self._pressed_keys = set()

    def get_fd_name(self):
        return self._device.fd.name

    def has_pressed_keys(self, keys):
        if not isinstance(keys, set):
            keys = set(keys)
        return len(keys) == len(self._pressed_keys & keys)

    def get_pressed_keys(self):
        return self._pressed_keys

    def create_uinput_device(self):
        devname = self.get_fd_name()
        dev = libevdev.Device(open(devname, 'rb'))
        dev.name = (dev.name or 'Input Device') + ' (Virtual)'
        return dev.create_uinput_device()

    def events(self):
        buf = []
        for event in self._device.events():
            # skip repeat
            if event.matches(libevdev.EV_KEY, 2):
                continue
            # update key state
            if event.matches(libevdev.EV_KEY):
                if event.value == 0:
                    self._pressed_keys -= {event.code}
                elif event.value == 1:
                    self._pressed_keys |= {event.code}
            # handle buffer
            buf.append(event)
            if event.matches(libevdev.EV_SYN.SYN_REPORT):
                # do nothing when SYN_REPORT is the only event
                if len(buf) > 1:
                    yield buf
                buf = []
