import threading

import libevdev

from .system_events import InputDeviceMonitor
from .grab import DeviceGrabManager

device_monitor = InputDeviceMonitor()
# device_monitor.add_monitored_attrs({
#   "ID_VENDOR_ID": "046d",
#   "ID_MODEL_ID": "c52b",
#   "ID_INPUT_KEYBOARD": "1",
#   "ID_INPUT_MOUSE": "1",
# })
device_monitor.add_monitored_attrs({
    "ID_VENDOR": "Apple_Inc.",
    "ID_INPUT_TOUCHPAD": "1",
})

def forward_uinput(udev_device):
    def _reader():
        fd = open(udev_device.get('DEVNAME'), 'rb')
        libevdev_device = libevdev.Device(fd)
        DeviceGrabManager(libevdev_device, udev_device).grab()
        libevdev_device.name = (libevdev_device.name or '') + ' (Virtual)'
        uinput_device = libevdev_device.create_uinput_device()
        buf = []
        for event in libevdev_device.events():
            buf.append(event)
            if event.matches(libevdev.EV_SYN.SYN_REPORT):
                uinput_device.send_events(buf)
                buf = []
    threading.Thread(target=_reader).start()

device_monitor.start(forward_uinput, lambda d: print(d))
