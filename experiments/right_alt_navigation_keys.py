from typing import (
    Iterable,
)
import libevdev

def run(log):
    input_codes = set()
    output_codes = set()

    input_codes.add(libevdev.EV_KEY.KEY_RIGHTALT)
    input_codes.add(libevdev.EV_SYN.SYN_REPORT)
    output_codes.add(libevdev.EV_SYN.SYN_REPORT)

    event_map = {
        libevdev.evbit(k): libevdev.evbit(v)
        for k, v in
        [
            # arrow
            ('KEY_H', 'KEY_LEFT'),
            ('KEY_J', 'KEY_DOWN'),
            ('KEY_K', 'KEY_UP'),
            ('KEY_L', 'KEY_RIGHT'),
            # home/end
            ('KEY_SEMICOLON', 'KEY_END'),
            ('KEY_P', 'KEY_HOME'),
            # pgup/pgdn
            ('KEY_APOSTROPHE', 'KEY_PAGEDOWN'),
            ('KEY_LEFTBRACE', 'KEY_PAGEUP'),
            # ins/del
            ('KEY_U', 'KEY_DELETE'),
            ('KEY_I', 'KEY_INSERT'),
        ]
    }

    for k, v in event_map.items():
        input_codes.add(k)
        output_codes.add(k)
        output_codes.add(v)

    key_states = {}
    def _is_pressed(code: libevdev.EventCode):
        return key_states.get(code, 0) > 0
    def _transform_event(event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
        if event.code == libevdev.EV_KEY.KEY_RIGHTALT:
            yield event
            key_states[event.code] = event.value
            return
        mapped_code = event_map.get(event.code)
        if mapped_code is not None and (_is_pressed(libevdev.EV_KEY.KEY_RIGHTALT) or _is_pressed(mapped_code)):
            yield libevdev.InputEvent(mapped_code, event.value)
            key_states[mapped_code] = event.value
        else:
            yield event
            key_states[event.code] = event.value

    return input_codes, output_codes, _transform_event
