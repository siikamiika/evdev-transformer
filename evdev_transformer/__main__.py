import threading
import random
import json

import libevdev

from .context import InputContext
from .serde import (
    serialize_events,
    deserialize_events
)
from .config import Config

logitech_k400 = {
    "ID_VENDOR_ID": "046d",
    "ID_MODEL_ID": "c52b",
    "ID_INPUT_KEYBOARD": "1",
    "ID_INPUT_MOUSE": "1",
}
apple_magic_trackpad = {
    "ID_VENDOR": "Apple_Inc.",
    "ID_INPUT_TOUCHPAD": "1",
}

with open('example_config.json') as f:
    config = Config.from_dict(json.load(f))

# for event in config.events():
#     print(event)

# print(json.dumps(config.to_dict(), indent=4))
# print(config._current_links)
# config.activate_next_link('Unholy Alliance')
# print(config._current_links)
# exit()

context = InputContext()
context.add_monitored_attrs(apple_magic_trackpad)

def handle_device(device, rule):
    devname = device.get_fd_name()
    uinput_device = device.create_uinput_device()
    for events in device.events():
        print(deserialize_events(serialize_events(events)))
        uinput_device.send_events(events)
        # if random.randint(0, 100) == 100:
        #     context.remove_monitored_attrs(logitech_k400)
        # elif random.randint(0, 100) == 100:
        #     context.add_monitored_attrs(logitech_k400)

for action, device, rule in context.events():
    print(action, device, rule)
    if action == 'add':
        threading.Thread(target=handle_device, args=(device, rule)).start()
    elif action == 'remove':
        pass
