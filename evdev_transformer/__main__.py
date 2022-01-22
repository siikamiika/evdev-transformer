import libevdev

from .context import InputContext

context = InputContext()
context.add_monitored_attrs({
    "ID_VENDOR_ID": "046d",
    "ID_MODEL_ID": "c52b",
    "ID_INPUT_KEYBOARD": "1",
    "ID_INPUT_MOUSE": "1",
})
# context.add_monitored_attrs({
#     "ID_VENDOR": "Apple_Inc.",
#     "ID_INPUT_TOUCHPAD": "1",
# })

for action, device, rule in context.events():
    print(action, device, rule)
    if action == 'add':
        uinput_device = device.create_uinput_device()
        for events in device.events():
            print(events)
            uinput_device.send_events(events)
