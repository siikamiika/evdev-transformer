from __future__ import annotations
from typing import (
    Dict,
    List,
    Set,
    Iterable,
    Optional,
)
import threading

import libevdev

class SourceDevice:
    def __init__(self, device, identifier):
        self._device = device
        self._identifier = identifier
        self._pressed_keys: Set[int] = set()
        self._abs_mt_tracking_ids_by_slot: Dict[int, int] = {}
        self._prev_slot: Optional[int] = None
        self._event_loop_stop_count: int = 0
        self._buffer: List[libevdev.InputEvent] = []
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        raise NotImplementedError('Override me')

    @property
    def id(self) -> Dict[str, int]:
        raise NotImplementedError('Override me')

    @property
    def evbits(self) -> Dict[libevdev.EventType, List[libevdev.EventCode]]:
        raise NotImplementedError('Override me')

    @property
    def absinfo(self) -> Dict[libevdev.EventCode, libevdev.InputAbsInfo]:
        raise NotImplementedError('Override me')

    @property
    def rep_value(self) -> Dict[libevdev.EventCode, int]:
        raise NotImplementedError('Override me')

    @property
    def identifier(self):
        return self._identifier

    @property
    def pressed_keys(self) -> Set[int]:
        return self._pressed_keys

    def has_pressed_keys(self, keys: Iterable[int]) -> bool:
        if not isinstance(keys, set):
            keys = set(keys)
        return len(keys) == len(self._pressed_keys & keys)

    def release(self):
        self._event_loop_stop_count += 1

    def events(self) -> Iterable[List[libevdev.InputEvent]]:
        try:
            with self._lock:
                self._grab_device()
                yield from self._init_attached_device()
                for events in self._events():
                    print(self._event_loop_stop_count, self._pressed_keys, self._abs_mt_tracking_ids_by_slot)
                    if self._event_loop_stop_count > 0:
                        yield from self._cleanup_released_device()
                        break
                    yield events
        finally:
            self._event_loop_stop_count = max(self._event_loop_stop_count - 1, 0)

    def _release_device(self):
        raise NotImplementedError('Override me')

    def _grab_device(self):
        raise NotImplementedError('Override me')

    def _events(self):
        raise NotImplementedError('Override me')

    # TODO group by event type
    def _handle_event(
        self,
        event: libevdev.InputEvent,
    ) -> Iterable[List[libevdev.InputEvent]]:
        # skip repeat
        if event.matches(libevdev.EV_KEY, 2):
            return
        # update key state
        if event.matches(libevdev.EV_KEY):
            if event.value == 0:
                self._pressed_keys -= {event.code}
            elif event.value == 1:
                self._pressed_keys |= {event.code}
        # https://www.kernel.org/doc/Documentation/input/multi-touch-protocol.txt
        if event.matches(libevdev.EV_ABS.ABS_MT_SLOT):
            self._prev_slot = event.value
        elif event.matches(libevdev.EV_ABS.ABS_MT_TRACKING_ID):
            if self._prev_slot is None:
                for slot in self._abs_mt_tracking_ids_by_slot:
                    self._prev_slot = slot
                    break
            if self._prev_slot:
                if event.value == -1:
                    try:
                        del self._abs_mt_tracking_ids_by_slot[self._prev_slot]
                    except KeyError:
                        pass
                else:
                    self._abs_mt_tracking_ids_by_slot[self._prev_slot] = event.value
        # handle buffer
        self._buffer.append(event)
        if event.matches(libevdev.EV_SYN.SYN_REPORT):
            # do nothing when SYN_REPORT is the only event
            if len(self._buffer) > 1:
                yield self._buffer
            self._buffer = []
            self._prev_slot = None

    def _init_attached_device(self) -> Iterable[List[libevdev.InputEvent]]:
        # restore multi touch slots
        # TODO expiration?
        for slot, tracking_id in self._abs_mt_tracking_ids_by_slot.items():
            yield [
                libevdev.InputEvent(libevdev.EV_ABS.ABS_MT_SLOT, slot),
                libevdev.InputEvent(libevdev.EV_ABS.ABS_MT_TRACKING_ID, tracking_id),
                libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
            ]

    def _cleanup_released_device(self) -> Iterable[List[libevdev.InputEvent]]:
        # release keys
        for code in self._pressed_keys:
            yield [
                libevdev.InputEvent(code, 0),
                libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
            ]
        # reset multi touch slots
        if any(b == libevdev.EV_ABS.ABS_MT_TRACKING_ID for b in self.evbits.get(libevdev.EV_ABS, [])):
            yield [
                libevdev.InputEvent(libevdev.EV_ABS.ABS_MT_TRACKING_ID, -1),
                libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
            ]
        for slot, tracking_id in self._abs_mt_tracking_ids_by_slot.items():
            yield [
                libevdev.InputEvent(libevdev.EV_ABS.ABS_MT_SLOT, slot),
                libevdev.InputEvent(libevdev.EV_ABS.ABS_MT_TRACKING_ID, -1),
                libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
            ]
        # reset internal state except for multi touch so that it can be initialized on reattach
        self._pressed_keys = set()
        self._release_device()

class EvdevSourceDevice(SourceDevice):
    @classmethod
    def from_udev(
        cls,
        udev_device: Dict[str, str],
        rule: Dict[str, str],
    ) -> EvdevSourceDevice:
        devname = udev_device.get('DEVNAME')
        if devname is None:
            raise Exception('DEVNAME is missing')
        fd = open(devname, 'rb')
        return cls(libevdev.Device(fd), rule)

    @property
    def name(self) -> str:
        return self._device.name

    @property
    def id(self):
        return self._device.id

    @property
    def evbits(self) -> Dict[libevdev.EventType, List[libevdev.EventCode]]:
        return self._device.evbits

    @property
    def absinfo(self) -> Dict[libevdev.EventCode, libevdev.InputAbsInfo]:
        return {
            c: self._device.absinfo[c]
            for c in self._device.evbits.get(libevdev.EV_ABS, [])
        }

    @property
    def rep_value(self) -> Dict[libevdev.EventCode, int]:
        return {
            c: self._device.value[c]
            for c in self._device.evbits.get(libevdev.EV_REP, [])
        }

    def _release_device(self):
        self._device.ungrab()

    def _grab_device(self):
        self._device.grab()

    def _events(self):
        while True:
            try:
                for event in self._device.events():
                    yield from self._handle_event(event)
            except libevdev.device.EventsDroppedException:
                for event in self._device.sync():
                    yield from self._handle_event(event)
                continue
            break

class SubprocessSourceDevice(SourceDevice):
    pass

class DestinationDevice:
    def __init__(
        self,
        name: str,
        id: Dict[str, int],
        evbits: Dict[libevdev.EventType, List[libevdev.EventCode]],
        absinfo: Dict[libevdev.EventCode, libevdev.InputAbsInfo],
        rep_value: Dict[libevdev.EventCode, int],
        properties: Optional[Dict],
    ):
        self._name = name
        self._id = id
        self._evbits = evbits
        self._absinfo = absinfo
        self._rep_value = rep_value
        self._properties = properties
        self._device = self._create_device()

    @classmethod
    def create(
        cls,
        source_device: SourceDevice,
        properties: Dict = None,
    ) -> DestinationDevice:
        return cls(
            source_device.name + ' (Virtual)',
            source_device.id,
            source_device.evbits,
            source_device.absinfo,
            source_device.rep_value,
            properties,
        )

    def send_events(self, events: List[libevdev.InputEvent]):
        raise NotImplementedError('Override me')

    def _create_device(self):
        raise NotImplementedError('Override me')

class UinputDestinationDevice(DestinationDevice):
    def send_events(self, events: List[libevdev.InputEvent]):
        self._device.send_events(events)

    def _create_device(self) -> libevdev.device.UinputDevice:
        device = libevdev.Device()
        device.name = self._name
        device.id = self._id
        for type_, evbits in self._evbits.items():
            for evbit in evbits:
                if type_ == libevdev.EV_ABS:
                    data = self._absinfo[evbit]
                elif type_ == libevdev.EV_REP:
                    data = self._rep_value[evbit]
                else:
                    data = None
                device.enable(evbit, data)

        # TODO is this a bug in libevdev
        # for p in self.properties:
        #     self.enable(p)

        return device.create_uinput_device()

class SubprocessDestinationDevice(DestinationDevice):
    def send_events(self, events: List[libevdev.InputEvent]):
        # TODO
        print(events)

    def _create_device(self) -> libevdev.device.UinputDevice:
        print('TODO SubprocessDestinationDevice._create_device')

class HidGadgetDestinationDevice(DestinationDevice):
    # TODO
    # https://github.com/siikamiika/hid-emu
    # https://www.kernel.org/doc/Documentation/usb/gadget_hid.txt
    pass
