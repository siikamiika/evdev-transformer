#!/usr/bin/env python3

import libinput

li = libinput.LibInput(context_type=libinput.ContextType.PATH)
device = li.add_device('/dev/input/by-id/usb-Apple_Inc._Magic_Trackpad_CC2142302BD0W5WAK-if01-event-mouse')

# device.config.send_events.set_mode(libinput.SendEventsMode.DISABLED)
device.config.tap.set_button_map(libinput.TapButtonMap.LRM)
device.config.click.set_method(libinput.ClickMethod.CLICKFINGER)

# print(device.config.send_events.mode)
print(device.config.tap.button_map)
print(device.config.click.method)

pointer_axes = [
    libinput.PointerAxis.SCROLL_HORIZONTAL,
    libinput.PointerAxis.SCROLL_VERTICAL,
]

for event in li.events:
    event_type_text = f'{event.__class__.__name__}.{event.type.name}'
    if isinstance(event, libinput.PointerEvent):
        if event.type == libinput.EventType.POINTER_MOTION:
            print({
                'type': event_type_text,
                'delta': event.delta,
                'delta_unaccelerated': event.delta_unaccelerated,
            })
        elif event.type == libinput.EventType.POINTER_AXIS:
            print({
                'type': event_type_text,
                'source': event.axis_source.name,
                'delta': tuple(event.get_axis_value(a) if event.has_axis(a) else 0.0 for a in pointer_axes),
                # TODO doesn't work
                'delta_unaccelerated': tuple(event.get_axis_value_discrete(a) if event.has_axis(a) else 0.0 for a in pointer_axes),
            })
        elif event.type == libinput.EventType.POINTER_BUTTON:
            print({
                'type': event_type_text,
                'button': event.button,
                'button_state': event.button_state.name,
            })
        else:
            print({
                'type': event_type_text,
            })
            raise Exception('TODO')
    elif isinstance(event, libinput.GestureEvent):
        # swipe
        if event.type == libinput.EventType.GESTURE_SWIPE_BEGIN:
            print({
                'type': event_type_text,
                'fingers': event.finger_count,
            })
        elif event.type == libinput.EventType.GESTURE_SWIPE_UPDATE:
            print({
                'type': event_type_text,
                'fingers': event.finger_count,
                'delta': event.delta,
                'delta_unaccelerated': event.delta_unaccelerated,
            })
        elif event.type == libinput.EventType.GESTURE_SWIPE_END:
            print({
                'type': event_type_text,
                'fingers': event.finger_count,
                'cancelled': event.cancelled,
            })
        # pinch
        elif event.type == libinput.EventType.GESTURE_PINCH_BEGIN:
            print({
                'type': event_type_text,
                'fingers': event.finger_count,
                'scale': event.scale,
            })
        elif event.type == libinput.EventType.GESTURE_PINCH_UPDATE:
            print({
                'type': event_type_text,
                'fingers': event.finger_count,
                'scale': event.scale,
                'delta': event.delta,
                'delta_unaccelerated': event.delta_unaccelerated,
                'angle_delta': event.angle_delta,
                'scale': event.scale,
            })
        elif event.type == libinput.EventType.GESTURE_PINCH_END:
            print({
                'type': event_type_text,
                'fingers': event.finger_count,
                'cancelled': event.cancelled,
                'scale': event.scale,
            })
        # hold
        elif event.type == libinput.EventType.GESTURE_HOLD_BEGIN:
            print({
                'type': event_type_text,
                'fingers': event.finger_count,
            })
        elif event.type == libinput.EventType.GESTURE_HOLD_END:
            print({
                'type': event_type_text,
                'fingers': event.finger_count,
            })
        else:
            print({
                'type': event_type_text,
            })
            raise Exception('TODO')
    elif isinstance(event, libinput.DeviceNotifyEvent):
        print(
            type(event),
            event.type,
        )
    elif isinstance(event, libinput.TouchEvent):
        print(type(event), event.type)
        raise Exception('TODO')
    elif isinstance(event, libinput.TabletToolEvent):
        print(type(event), event.type)
        raise Exception('TODO')
    elif isinstance(event, libinput.TabletPadEvent):
        print(type(event), event.type)
        raise Exception('TODO')
    elif isinstance(event, libinput.SwitchEvent):
        print(type(event), event.type)
        raise Exception('TODO')
    elif isinstance(event, libinput.KeyboardEvent):
        print(type(event), event.type)
        raise Exception('TODO')
