import json

import libevdev

def serialize_events(events):
    return json.dumps([
        {'type': e.type.value, 'code': e.code.value, 'value': e.value}
        for e in events
    ], ensure_ascii=False).encode('utf-8')

def deserialize_events(events):
    event_dicts = json.loads(events.decode('utf-8'))
    return [
        libevdev.InputEvent(libevdev.evbit(d['type'], d['code']), d['value'])
        for d in event_dicts
    ]
