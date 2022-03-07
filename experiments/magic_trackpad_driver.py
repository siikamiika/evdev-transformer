from typing import (
    Iterable,
)
import libevdev

log = None

def init(l, g):
    global log
    input_codes = l['input_codes']
    output_codes = l['output_codes']
    log = g['log']

    input_codes.add(libevdev.EV_ABS.ABS_MT_POSITION_X)
    input_codes.add(libevdev.EV_ABS.ABS_MT_POSITION_Y)
    output_codes.add(libevdev.EV_REL.REL_X)
    output_codes.add(libevdev.EV_REL.REL_Y)

def _transform_event(event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
    if log is not None:
        log.debug(f'magic_trackpad_driver.py: {event}')
    yield event
