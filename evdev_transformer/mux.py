import queue
import threading

import libevdev

from .libinput_touchpad import LibinputTouchpadEventSource
from .grab import DeviceGrabManager

class DeviceMuxer:
    def __init__(self):
        self._event_queue = queue.Queue()

    def events(self):
        while True:
            yield self._event_queue.get()

    def add_device(self, udev_device):
        for device in self._iter_devices(udev_device):
            self._start_device_reader(device)

    def _start_device_reader(self, device):
        def _reader():
            for event in device.events():
                self._event_queue.put((device, event))
        threading.Thread(target=_reader).start()

    def _iter_devices(self, udev_device):
        libevdev_device = self._udev_to_libevdev(udev_device)
        DeviceGrabManager(libevdev_device, udev_device).grab()
        yield libevdev_device
        if udev_device.get('ID_INPUT_TOUCHPAD'):
            yield LibinputTouchpadEventSource(libevdev_device)

    def _udev_to_libevdev(self, udev_device):
        devname = udev_device.get('DEVNAME')
        fd = open(devname, 'rb')
        return libevdev.Device(fd)
