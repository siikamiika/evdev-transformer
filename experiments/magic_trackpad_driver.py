from typing import (
    Iterable,
)
import libevdev

def run(log):
    input_codes = set()
    output_codes = set()

    input_codes.add(libevdev.EV_ABS.ABS_MT_POSITION_X)
    input_codes.add(libevdev.EV_ABS.ABS_MT_POSITION_Y)
    output_codes.add(libevdev.EV_REL.REL_X)
    output_codes.add(libevdev.EV_REL.REL_Y)

    def _transform_event(event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
        log.debug(f'magic_trackpad_driver.py: {event}')
        yield event

    return input_codes, output_codes, _transform_event
