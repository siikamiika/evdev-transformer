from __future__ import annotations
from typing import (
    Dict,
    List,
    Set,
    Iterable,
    Optional,
    Callable,
    Tuple,
)
import threading
import subprocess
import json
import socket
import functools

import libevdev

from .config import (
    ConfigManager,
    Activator,
    HotkeyActivator,
)

class SourceDevice:
    def __init__(self, device, identifier):
        self._device = device
        self._identifier = identifier
        self._activators: List[Tuple[Activator, Callable]] = []
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

    def set_activators(self, activators: List[Tuple[Activator, Callable]]):
        self._activators = activators

    def has_pressed_keys(self, keys: Iterable[libevdev.EventCode]) -> bool:
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
                    # print(self._event_loop_stop_count, self._pressed_keys, self._abs_mt_tracking_ids_by_slot)
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
        # TODO script activators
        if event.matches(libevdev.EV_KEY, 1):
            for activator, activate in self._activators:
                if isinstance(activator, HotkeyActivator):
                    if (
                        activator.key == event.code.name
                        and self.has_pressed_keys([
                            # TODO resolve evbit in config?
                            libevdev.evbit(c)
                            for c in activator.modifiers
                        ])
                    ):
                        activate()
                        return
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
        for slot, tracking_id in self._abs_mt_tracking_ids_by_slot.items():
            yield [
                libevdev.InputEvent(libevdev.EV_ABS.ABS_MT_SLOT, slot),
                libevdev.InputEvent(libevdev.EV_ABS.ABS_MT_TRACKING_ID, -1),
                libevdev.InputEvent(libevdev.EV_SYN.SYN_REPORT, 0),
            ]
        if any(b == libevdev.EV_ABS.ABS_MT_TRACKING_ID for b in self.evbits.get(libevdev.EV_ABS, [])):
            yield [
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
        device = libevdev.Device(fd)
        device.grab()
        return cls(device, rule)

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
        # TODO only release when forwarded to itself explicitly (unimplemented)
        # self._device.ungrab()
        return

    def _grab_device(self):
        # see note for _release_device
        # self._device.grab()
        return

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

class UnixSocketSourceDevice(SourceDevice):
    @classmethod
    def from_ipc(
        cls,
        details: Dict,
        events: Iterable[Dict],
    ):
        class _Device:
            def __init__(self, details, events):
                self.details = details
                self._events = events
            def events(self):
                for events in self._events:
                    for event in events['events']:
                        yield libevdev.InputEvent(
                            libevdev.evbit(event['type'], event['code']),
                            event['value']
                        )
        device = _Device(details['data'], events)
        identifier = {
            'host': details['host'],
            'vendor': details['vendor'],
            'product': details['product'],
        }
        return cls(device, identifier)

    @property
    def name(self) -> str:
        return self._device.details['name']

    @property
    def id(self) -> Dict[str, int]:
        return self._device.details['id']

    @property
    @functools.cache
    def evbits(self) -> Dict[libevdev.EventType, List[libevdev.EventCode]]:
        return {
            libevdev.evbit(int(t)): [libevdev.evbit(int(t), c) for c in cs]
            for t, cs
            in self._device.details['evbits'].items()
        }

    @property
    @functools.cache
    def absinfo(self) -> Dict[libevdev.EventCode, libevdev.InputAbsInfo]:
        return {
            libevdev.evbit('EV_ABS', int(c)): libevdev.InputAbsInfo(**ai)
            for c, ai
            in self._device.details['absinfo'].items()
        }

    @property
    @functools.cache
    def rep_value(self) -> Dict[libevdev.EventCode, int]:
        return {
            libevdev.evbit('EV_REP', int(c)): v
            for c, v in self._device.details['rep_value'].items()
        }

    def _release_device(self):
        return

    def _grab_device(self):
        return

    def _events(self):
        for event in self._device.events():
            yield from self._handle_event(event)

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
        self._properties = properties or {}
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
        self._device.send_events(events)

    def _create_device(self):
        raise NotImplementedError('Override me')

class UinputDestinationDevice(DestinationDevice):
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
    # TODO watchdog
    def _create_device(self):
        class _SubprocessDevice:
            def __init__(self, command: str, details: Dict):
                self._command = command
                self._handle = self._create_handle()
                self._details = details
                self._host = socket.gethostname()
                self._details_sent = False
            def send_events(self, events: List[libevdev.InputEvent]):
                if not self._details_sent:
                    self._send_details()
                self._send_data(json.dumps({
                    'events': [
                        {'type': e.type.value, 'code': e.code.value, 'value': e.value}
                        for e in events
                    ]
                }).encode('utf-8'))
            def _send_details(self):
                data = json.dumps({
                    'host': self._host,
                    'vendor': self._details['id']['vendor'],
                    'product': self._details['id']['product'],
                    'data': self._details,
                }).encode('utf-8')
                self._send_data(data)
                self._details_sent = True
            def _send_data(self, data: bytes):
                try:
                    if self._handle.stdin is None:
                        raise AttributeError
                    self._handle.stdin.write(data + b'\n')
                    self._handle.stdin.flush()
                except (BrokenPipeError, AttributeError):
                    print('Created new handle')
                    self._handle = self._create_handle()
                    self._details_sent = False
            def _create_handle(self) -> subprocess.Popen:
                # TODO two-way communication? ACK etc
                return subprocess.Popen(self._command, stdin=subprocess.PIPE, shell=True)
        return _SubprocessDevice(self._properties['command'], self._serialize())

    def _serialize(self) -> Dict:
        return {
            'type': type(self).__name__,
            'name': self._name,
            'id': self._id,
            'evbits': {
                t.value: [sc.value for sc in c]
                for t, c
                in self._evbits.items()
            },
            'absinfo': {
                c.value: {
                    'minimum': ai.minimum,
                    'maximum': ai.maximum,
                    'fuzz': ai.fuzz,
                    'flat': ai.flat,
                    'resolution': ai.resolution,
                    'value': ai.value,
                }
                for c, ai in self._absinfo.items()
            },
            'rep_value': {
                c.value: v
                for c, v in self._rep_value.items()
            },
        }

class HidGadgetDestinationDevice(DestinationDevice):
    # TODO
    # https://github.com/siikamiika/hid-emu
    # https://www.kernel.org/doc/Documentation/usb/gadget_hid.txt
    pass
