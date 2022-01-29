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
        self._event_loop_stopped: bool = False
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
        self._event_loop_stopped = True

    def events(self) -> Iterable[List[libevdev.InputEvent]]:
        with self._lock:
            self._grab_device()
            self._event_loop_stopped = False
            for events in self._events():
                print(self._event_loop_stopped, self._pressed_keys)
                yield events
                # TODO forcefully release the pressed keys
                if self._event_loop_stopped and not self._pressed_keys:
                    self._release_device()
                    break

    def _release_device(self):
        raise NotImplementedError('Override me')

    def _grab_device(self):
        raise NotImplementedError('Override me')

    def _events(self):
        raise NotImplementedError('Override me')

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
        # handle buffer
        self._buffer.append(event)
        if event.matches(libevdev.EV_SYN.SYN_REPORT):
            # do nothing when SYN_REPORT is the only event
            if len(self._buffer) > 1:
                yield self._buffer
            self._buffer = []

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
