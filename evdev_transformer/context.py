import threading
import queue

import libevdev

from .system_events import InputDeviceMonitor

class InputContext:
    def __init__(self):
        self._devices = []
        self._device_monitor = InputDeviceMonitor()
        self._event_queue = queue.Queue()

    def events(self):
        def _bg():
            for data in self._monitor():
                self._event_queue.put(('monitor', data))
        threading.Thread(target=_bg).start()
        while True:
            event_type, data = self._event_queue.get()
            if event_type == 'monitor':
                yield data
            elif event_type == 'remove':
                for device, rule in self._devices:
                    if rule == data:
                        self._devices.remove((device, rule))
                        device.release()
                        yield 'remove', device, rule
                        break


    def _monitor(self):
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
        self._event_queue.put(('remove', attrs))

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
                return device
        return None

class EvdevWrapper:
    def __init__(self, libevdev_device):
        self._device = libevdev_device
        self._device.grab()
        self._pressed_keys = set()
        self._stopped = False

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

    def release(self):
        self._device.ungrab()
        self._stopped = True

    def events(self):
        buf = []
        for event in self._device.events():
            if self._stopped:
                break
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
