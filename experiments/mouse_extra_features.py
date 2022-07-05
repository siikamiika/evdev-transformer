from typing import (
    Iterable,
    Dict,
)
import libevdev

def run(log):
    input_codes = set()
    output_codes = set()

    io_code_names = [
        'BTN_LEFT', 'BTN_RIGHT', 'BTN_MIDDLE',
        'BTN_SIDE', 'BTN_EXTRA',
        'REL_X', 'REL_Y',
        'REL_WHEEL', 'REL_HWHEEL',
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
    # TODO divmod 7
    scroll_remainder_by_code: Dict[libevdev.EventCode, int] = {}
    def _transform_event(event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
        # skip repeat so that EV_KEY value can only be 0 or 1
        if event.type == libevdev.EV_KEY and event.value == 2:
            return

        # relative
        if event.code == libevdev.EV_REL.REL_X:
            prev_btn_extra_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_EXTRA)
            if prev_btn_extra_event and prev_btn_extra_event.value == 1 and _event_occurrence_diff(event, prev_btn_extra_event) >= 0.18:
                direction = -1 if event.value < 0 else 1
                for _ in range(abs(event.value)):
                    yield libevdev.InputEvent(libevdev.EV_REL.REL_HWHEEL, direction)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
            else:
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
        elif event.code == libevdev.EV_REL.REL_Y:
            prev_btn_extra_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_EXTRA)
            if prev_btn_extra_event and prev_btn_extra_event.value == 1 and _event_occurrence_diff(event, prev_btn_extra_event) >= 0.18:
                # reversed on purpose
                direction = 1 if event.value < 0 else -1
                for _ in range(abs(event.value)):
                    yield libevdev.InputEvent(libevdev.EV_REL.REL_WHEEL, direction)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
            else:
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
        elif event.code == libevdev.EV_REL.REL_WHEEL:
            prev_btn_side_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_SIDE)
            if prev_btn_side_event and prev_btn_side_event.value == 1:
                if event.value < 0:
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_TAB, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_TAB, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                else:
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTSHIFT, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_TAB, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_TAB, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTSHIFT, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
            else:
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
        elif event.code == libevdev.EV_REL.REL_HWHEEL:
            yield event
            yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
        # button
        elif event.code == libevdev.EV_KEY.BTN_LEFT:
            prev_btn_side_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_SIDE)
            if prev_btn_side_event and prev_btn_side_event.value == 1 and event.value == 1:
                yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTMETA, 1)
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                yield libevdev.InputEvent(libevdev.EV_KEY.KEY_F, 1)
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                yield libevdev.InputEvent(libevdev.EV_KEY.KEY_F, 0)
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTMETA, 0)
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
            else:
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
        elif event.code == libevdev.EV_KEY.BTN_RIGHT:
            yield event
            yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
        elif event.code == libevdev.EV_KEY.BTN_MIDDLE:
            prev_btn_side_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_SIDE)
            prev_btn_extra_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_EXTRA)
            if prev_btn_side_event and prev_btn_side_event.value == 1:
                if event.value == 1:
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_W, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_W, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
            elif prev_btn_extra_event and prev_btn_extra_event.value == 1:
                if event.value == 1:
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTSHIFT, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_T, 1)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_T, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTCTRL, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                    yield libevdev.InputEvent(libevdev.EV_KEY.KEY_LEFTSHIFT, 0)
                    yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
            else:
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
        elif event.code == libevdev.EV_KEY.BTN_SIDE:
            prev_btn_side_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_SIDE)
            if (
                prev_btn_side_event
                and event.value == 0
                and _event_occurrence_diff(event, prev_btn_side_event) < 0.18
            ):
                yield libevdev.InputEvent(libevdev.EV_KEY.BTN_SIDE, 1)
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
        elif event.code == libevdev.EV_KEY.BTN_EXTRA:
            prev_btn_extra_event = prev_events_by_code.get(libevdev.EV_KEY.BTN_EXTRA)
            if (
                prev_btn_extra_event
                and event.value == 0
                and (
                    (event.sec + event.usec / 10 ** 6)
                    - (prev_btn_extra_event.sec + prev_btn_extra_event.usec / 10 ** 6)
                ) < 0.18
            ):
                yield libevdev.InputEvent(libevdev.EV_KEY.BTN_EXTRA, 1)
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
                yield event
                yield libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 1)
        prev_events_by_code[event.code] = event

    return input_codes, output_codes, _transform_event
