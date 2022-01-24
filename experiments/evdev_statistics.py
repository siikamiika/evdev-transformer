#!/usr/bin/env python3

import sys
import collections
import json

import libevdev

fd = open(sys.argv[1], 'rb')
device = libevdev.Device(fd)

events = []
for event in device.events():
    events.append(event)
    if len(events) > 5000:
        break
print(json.dumps(dict(collections.Counter([f'{e.type.name}.{e.code.name}' for e in events]))))
