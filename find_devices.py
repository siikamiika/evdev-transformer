#!/usr/bin/env python3

import json

import pyudev

context = pyudev.Context()
properties = [
    'ID_VENDOR',
    'ID_MODEL',
    'ID_VENDOR_ID',
    'ID_MODEL_ID',
    'MAJOR',
    'MINOR',
    'DEVNAME',
    'ID_INPUT_KEYBOARD',
    'ID_INPUT_MOUSE',
    'ID_INPUT_TOUCHPAD',
]
required = [
    'ID_VENDOR_ID',
    'ID_MODEL_ID',
    'MAJOR',
    'MINOR',
]
one_of = [
    'ID_INPUT_KEYBOARD',
    'ID_INPUT_MOUSE',
    'ID_INPUT_TOUCHPAD',
]
for device in context.list_devices(subsystem='input'):
    device_data = {k: device.get(k) or '' for k in properties}
    if (
        all(device_data[k] for k in required)
        and device_data['DEVNAME'].startswith('/dev/input/event')
        and any(device_data[k] for k in one_of)
    ):
        print(json.dumps(device_data))
