#!/usr/bin/env python3

import json
import sys

import pyudev

rule = {}
if len(sys.argv) > 1:
    rule = json.loads(sys.argv[1])

context = pyudev.Context()
one_of = [
    'ID_INPUT_KEYBOARD',
    'ID_INPUT_MOUSE',
    'ID_INPUT_TOUCHPAD',
    'ID_INPUT_TABLET',
    'ID_INPUT_TOUCHSCREEN',
    'ID_INPUT_JOYSTICK',
]
for device in context.list_devices(subsystem='input'):
    device_data = {k: device.get(k, '') for k in device.properties}
    if (
        device_data.get('DEVNAME', '').startswith('/dev/input/event')
        and not device_data.get('DEVPATH', '').startswith('/devices/virtual/')
        and any(device_data.get(k) for k in one_of)
        and all(device_data.get(k) == v for k, v in rule.items())
    ):
        print(json.dumps(device_data))
