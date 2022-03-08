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

    mod_pressed = False
    def _transform_event(event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
        nonlocal mod_pressed
        if event.code == libevdev.EV_KEY.KEY_RIGHTALT:
            mod_pressed = bool(event.value)
            yield event
        elif mod_pressed and event.code in event_map:
            yield libevdev.InputEvent(event_map[event.code], event.value)
        else:
            yield event

    return input_codes, output_codes, _transform_event
