from typing import (
    Iterable,
)
import libevdev

def run(log):
    input_codes = set()
    output_codes = set()

    # key
    # input_codes.add(libevdev.EV_KEY.BTN_LEFT)
    input_codes.add(libevdev.EV_KEY.BTN_TOOL_FINGER)
    input_codes.add(libevdev.EV_KEY.BTN_TOOL_QUINTTAP)
    input_codes.add(libevdev.EV_KEY.BTN_TOUCH)
    input_codes.add(libevdev.EV_KEY.BTN_TOOL_DOUBLETAP)
    input_codes.add(libevdev.EV_KEY.BTN_TOOL_TRIPLETAP)
    input_codes.add(libevdev.EV_KEY.BTN_TOOL_QUADTAP)
    # abs
    input_codes.add(libevdev.EV_ABS.ABS_X)
    input_codes.add(libevdev.EV_ABS.ABS_Y)
    input_codes.add(libevdev.EV_ABS.ABS_PRESSURE)
    input_codes.add(libevdev.EV_ABS.ABS_MT_POSITION_X)
    input_codes.add(libevdev.EV_ABS.ABS_MT_POSITION_Y)
    input_codes.add(libevdev.EV_ABS.ABS_MT_TOUCH_MAJOR)
    input_codes.add(libevdev.EV_ABS.ABS_MT_TOUCH_MINOR)
    input_codes.add(libevdev.EV_ABS.ABS_MT_SLOT)
    input_codes.add(libevdev.EV_ABS.ABS_MT_TRACKING_ID)
    input_codes.add(libevdev.EV_ABS.ABS_MT_ORIENTATION)
    input_codes.add(libevdev.EV_ABS.ABS_MT_PRESSURE)
    # syn
    input_codes.add(libevdev.EV_SYN.SYN_REPORT)

    output_codes.add(libevdev.EV_REL.REL_X)
    output_codes.add(libevdev.EV_REL.REL_Y)
    output_codes.add(libevdev.EV_SYN.SYN_REPORT)

    driver = MagicTrackpadDriver()

    def _transform_event(event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
        for event2 in driver.handle_event(event):
            log.debug(f'magic_trackpad_driver.py: {event2}')
            yield event2

    return input_codes, output_codes, _transform_event

class MagicTrackpadDriver:
    def __init__(self):
        self._last_x = None
        self._last_y = None
        self._prev_slot = None

    def handle_event(self, event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
        if event.code == libevdev.EV_ABS.ABS_MT_SLOT:
            # TODO
            self._prev_slot = event.value
        elif event.code == libevdev.EV_ABS.ABS_X:
            rem = 0
            if self._last_x is not None:
                diff, rem = self._get_diff(event.value, self._last_x)
                yield libevdev.InputEvent(libevdev.EV_REL.REL_X, diff)
            self._last_x = event.value + rem
        elif event.code == libevdev.EV_ABS.ABS_Y:
            rem = 0
            if self._last_y is not None:
                diff, rem = self._get_diff(event.value, self._last_y)
                yield libevdev.InputEvent(libevdev.EV_REL.REL_Y, diff)
            self._last_y = event.value + rem
        elif event.code == libevdev.EV_KEY.BTN_TOUCH:
            if event.value == 0:
                self._last_x = self._last_y = None
        elif event.code == libevdev.EV_SYN.SYN_REPORT:
            yield event
            self._prev_slot = None

    def _get_diff(self, cur, prev):
        diff = cur - prev
        if diff >= 0:
            return diff // 4, diff % 4
        else:
            return -(-diff // 4), -(-diff % 4)
