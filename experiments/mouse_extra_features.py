from typing import (
    Iterable,
    Dict,
)
import libevdev

_SIDE_BUTTON_MODIFIER_DELAY = 0.18
_SCROLL_FACTOR = 0.2
_SCROLL_FACTOR_FAST = 2.0

def run(log):
    input_codes = set()
    output_codes = set()

    io_code_names = [
        'BTN_LEFT', 'BTN_RIGHT', 'BTN_MIDDLE',
        'BTN_SIDE', 'BTN_EXTRA',
        'REL_X', 'REL_Y',
        'REL_WHEEL', 'REL_HWHEEL', 'REL_WHEEL_HI_RES', 'REL_HWHEEL_HI_RES',
        'SYN_REPORT',
    ]
    out_code_names = [
        'KEY_LEFTCTRL', 'KEY_LEFTSHIFT', 'KEY_LEFTMETA',
        'KEY_W', 'KEY_T', 'KEY_F',
        'KEY_TAB',
    ]
    for code_name in io_code_names:
        code = libevdev.evbit(code_name)
        input_codes.add(code)
        output_codes.add(code)
    for code_name in out_code_names:
        output_codes.add(libevdev.evbit(code_name))

    def _event_occurrence_diff(event1, event2):
        return abs(
            (event1.sec + event1.usec / 10 ** 6)
            - (event2.sec + event2.usec / 10 ** 6)
        )

    prev_events_by_code: Dict[libevdev.EventCode, libevdev.InputEvent] = {}
    suppress_release_by_code: Dict[libevdev.EventCode, bool] = {}
    scroll_remainder_by_code: Dict[libevdev.EventCode, int] = {
        libevdev.EV_REL.REL_X: 0,
        libevdev.EV_REL.REL_Y: 0,
    }
    def _transform_event(event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
        # skip repeat so that EV_KEY value can only be 0 or 1
        if event.type == libevdev.EV_KEY and event.value == 2:
            return

        # relative
        if event.code == libevdev.EV_REL.REL_X:
            prev_btn_extra_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_EXTRA)
            if (
                prev_btn_extra_event
                and prev_btn_extra_event.value == 1
                and _event_occurrence_diff(event, prev_btn_extra_event) >= _SIDE_BUTTON_MODIFIER_DELAY
            ):
                prev_btn_right_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_RIGHT)
                direction = -1 if event.value < 0 else 1
                rem = event.value + scroll_remainder_by_code[libevdev.EV_REL.REL_X]
                step = (1 / _SCROLL_FACTOR_FAST) if (prev_btn_right_event and prev_btn_right_event.value == 1) else (1 / _SCROLL_FACTOR)
                while direction * rem > step:
                    yield libevdev.InputEvent(libevdev.EV_REL.REL_HWHEEL, direction)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    rem -= direction * step
                scroll_remainder_by_code[libevdev.EV_REL.REL_X] = rem
            else:
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
        elif event.code == libevdev.EV_REL.REL_Y:
            prev_btn_extra_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_EXTRA)
            if (
                prev_btn_extra_event
                and prev_btn_extra_event.value == 1
                and _event_occurrence_diff(event, prev_btn_extra_event) >= _SIDE_BUTTON_MODIFIER_DELAY
            ):
                prev_btn_right_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_RIGHT)
                direction = -1 if event.value < 0 else 1
                rem = event.value + scroll_remainder_by_code[libevdev.EV_REL.REL_Y]
                step = (1 / _SCROLL_FACTOR_FAST) if (prev_btn_right_event and prev_btn_right_event.value == 1) else (1 / _SCROLL_FACTOR)
                while direction * rem > step:
                    # reversed on purpose
                    yield libevdev.InputEvent(libevdev.EV_REL.REL_WHEEL, -direction)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    rem -= direction * step
                scroll_remainder_by_code[libevdev.EV_REL.REL_Y] = rem
            else:
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
        elif event.code == libevdev.EV_REL.REL_WHEEL:
            prev_btn_side_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_SIDE)
            if prev_btn_side_event and prev_btn_side_event.value == 1:
                if event.value < 0:
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_TAB, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_TAB, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                else:
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTSHIFT, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_TAB, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_TAB, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTSHIFT, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
            else:
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
        elif event.code == libevdev.EV_REL.REL_HWHEEL:
            yield event
            yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
        # button
        elif event.code == libevdev.EV_KEY.BTN_LEFT:
            prev_btn_side_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_SIDE)
            if prev_btn_side_event and prev_btn_side_event.value == 1 and event.value == 1:
                yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTMETA, 1)
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                yield libevdev.InputEvent(libevdev.EV_KEY.KEY_F, 1)
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                yield libevdev.InputEvent(libevdev.EV_KEY.KEY_F, 0)
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTMETA, 0)
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
            else:
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
        elif event.code == libevdev.EV_KEY.BTN_RIGHT:
            # suppress when modifier button is pressed to be used as a multi-button modifier
            prev_btn_extra_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_EXTRA)
            if (
                prev_btn_extra_event
                and prev_btn_extra_event.value == 1
                and _event_occurrence_diff(event, prev_btn_extra_event) >= _SIDE_BUTTON_MODIFIER_DELAY
            ):
                if event.value == 1:
                    suppress_release_by_code[event.code] = True
            else:
                if not suppress_release_by_code.get(event.code):
                    yield event
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
            if event.value == 0 and suppress_release_by_code.get(event.code):
                suppress_release_by_code[event.code] = False
        elif event.code == libevdev.EV_KEY.BTN_MIDDLE:
            prev_btn_side_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_SIDE)
            prev_btn_extra_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_EXTRA)
            if prev_btn_side_event and prev_btn_side_event.value == 1:
                if event.value == 1:
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_W, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_W, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
            elif prev_btn_extra_event and prev_btn_extra_event.value == 1:
                if event.value == 1:
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTSHIFT, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_T, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_T, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTSHIFT, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
            else:
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
        elif event.code == libevdev.EV_KEY.BTN_SIDE:
            prev_btn_side_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_SIDE)
            if (
                prev_btn_side_event
                and prev_btn_side_event.value == 1
                and event.value == 0
                and _event_occurrence_diff(event, prev_btn_side_event) < _SIDE_BUTTON_MODIFIER_DELAY
            ):
                yield libevdev.InputEvent(libevdev.EV_KEY.BTN_SIDE, 1)
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
        elif event.code == libevdev.EV_KEY.BTN_EXTRA:
            prev_btn_extra_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_EXTRA)
            if (
                prev_btn_extra_event
                and prev_btn_extra_event.value == 1
                and event.value == 0
                and _event_occurrence_diff(event, prev_btn_extra_event) < _SIDE_BUTTON_MODIFIER_DELAY
            ):
                yield libevdev.InputEvent(libevdev.EV_KEY.BTN_EXTRA, 1)
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0)
        prev_events_by_code[event.code] = event

    return input_codes, output_codes, _transform_event
