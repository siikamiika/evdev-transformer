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
device_monitor.start(muxer.add_device, lambda d: print(d))

for device, event in muxer.events():
    print(device, event)
