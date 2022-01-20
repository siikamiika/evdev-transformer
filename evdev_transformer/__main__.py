import libevdev

from .virtual_devices import Keyboard, AppleTrackpad
from .mux import DeviceMuxer
from .system_events import InputDeviceMonitor

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

muxer = DeviceMuxer()

def udev_to_libevdev(udev_device):
    devname = udev_device.get('DEVNAME')
    fd = open(devname, 'rb')
    return libevdev.Device(fd)

def mux_device(udev_device):
    # TODO touchpad libinput
    # "grab":
    # swaymsg input '1452:613:Apple_Inc._Magic_Trackpad_2' events enabled
    # (hex --> dec, device name)
    libevdev_device = udev_to_libevdev(udev_device)
    libevdev_device.grab()
    muxer.add_device(libevdev_device)

device_monitor.start(mux_device, lambda d: print(d))

for device, event in muxer.events():
    print(device, event)
