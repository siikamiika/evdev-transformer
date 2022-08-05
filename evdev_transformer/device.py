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
import time

import libevdev

from .config import (
    Activator,
)
from .transform import (
    EventTransform,
)
from .activator import (
    DeviceLinkActivator,
)
from . import log

class SourceDevice:
    def __init__(self, device, identifier):
        self._device = device
        self._identifier = identifier
        self._activators: List[DeviceLinkActivator] = []
        self._transforms: List[EventTransform] = []
        self._pressed_keys: Set[int] = set()
        self._abs_mt_tracking_ids_by_slot: Dict[int, int] = {}
        self._prev_slot: Optional[int] = None
        self._event_loop_stopped: bool = False
        self._buffer: List[libevdev.InputEvent] = []
        self._lock = threading.Lock()

    def __repr__(self) -> str:
        return f'{type(self).__name__}(name="{self.name}", identifier={self._identifier})'

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
    def input_properties(self) -> List[libevdev.InputProperty]:
        raise NotImplementedError('Override me')

    @property
    def identifier(self):
        return self._identifier

    @property
    def pressed_keys(self) -> Set[int]:
        return self._pressed_keys

    def set_activators(self, activators: List[Tuple[Activator, Callable]]):
        self._activators = [
            DeviceLinkActivator.create(activator, self.has_pressed_keys, activate)
            for activator, activate in activators
        ]

    def set_transforms(self, transforms: List[EventTransform]):
        self._transforms = transforms

    def has_pressed_keys(self, keys: Iterable[libevdev.EventCode]) -> bool:
        if not isinstance(keys, set):
            keys = set(keys)
        return len(keys) == len(self._pressed_keys & keys)

    def release(self):
        self._event_loop_stopped = True

    def events(self) -> Iterable[List[libevdev.InputEvent]]:
        try:
            with self._lock:
                self._grab_device()
                yield from self._init_attached_device()
                for events in self._events():
                    if self._event_loop_stopped:
                        yield from self._cleanup_released_device()
                        break
                    yield events
        finally:
            self._event_loop_stopped = False

    def _release_device(self):
        raise NotImplementedError('Override me')

    def _grab_device(self):
        raise NotImplementedError('Override me')

    def _events(self):
        raise NotImplementedError('Override me')

    def _transform_event(self, event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
        buffer = [event]
        for transform in self._transforms:
            transformed_buffer = []
            for intermediate_event in buffer:
                if transform.matches_event(intermediate_event):
                    for transformed_event in transform.transform_event(intermediate_event):
                        transformed_buffer.append(transformed_event)
                else:
                    transformed_buffer.append(intermediate_event)
            buffer = transformed_buffer
        yield from buffer

    def _handle_event(
        self,
        event: libevdev.InputEvent,
    ) -> Iterable[List[libevdev.InputEvent]]:
        for transformed_event in self._transform_event(event):
            for activator in self._activators:
                if activator.matches_event(transformed_event):
                    activator.activate()
                    # TODO is this correct with multi touch protocol and EV_MSC
                    self._buffer = []
                    break
            else:
                yield from self._handle_event2(transformed_event)

    def _handle_event2(
        self,
        event: libevdev.InputEvent,
    ) -> Iterable[List[libevdev.InputEvent]]:
        if event.type == libevdev.EV_KEY:
            # release key
            if event.value == 0:
                self._pressed_keys -= {event.code}
            # press key
            elif event.value == 1:
                self._pressed_keys |= {event.code}
            # skip repeat
            elif event.value == 2:
                return
        elif event.type == libevdev.EV_ABS:
            # https://www.kernel.org/doc/Documentation/input/multi-touch-protocol.txt
            if event.code == libevdev.EV_ABS.ABS_MT_SLOT:
                self._prev_slot = event.value
            elif event.code == libevdev.EV_ABS.ABS_MT_TRACKING_ID:
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
        # # TODO use config
        # if libevdev.EV_REL not in self._device.evbits and libevdev.EV_ABS in self._device.evbits:
        #     import copy
        #     new = copy.deepcopy(self._device.evbits)
        #     new[libevdev.EV_REL] = [
        #         libevdev.EV_REL.REL_X,
        #         libevdev.EV_REL.REL_Y,
        #     ]
        #     return new
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

    @property
    def input_properties(self) -> List[libevdev.InputProperty]:
        return self._device.properties

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
                    # device descriptor was resent
                    if 'events' not in events:
                        continue
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

    @property
    @functools.cache
    def input_properties(self) -> List[libevdev.InputProperty]:
        return [libevdev.propbit(p) for p in self._device.details['properties']]

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
        input_properties: List[libevdev.InputProperty],
        properties: Optional[Dict],
    ):
        self._name = name
        self._id = id
        self._evbits = evbits
        self._absinfo = absinfo
        self._rep_value = rep_value
        self._input_properties = input_properties
        self._properties = properties or {}
        # if 'Apple' in name:
        #     # fake touchscreen
        #     self._input_properties = [libevdev.propbit('INPUT_PROP_DIRECT')]
        #     # fake tablet
        #     self._evbits[libevdev.evbit('EV_KEY')].remove(libevdev.evbit('BTN_TOOL_FINGER'))
        #     self._evbits[libevdev.evbit('EV_KEY')] += [
        #         libevdev.evbit('BTN_TOOL_PEN'),
        #         libevdev.evbit('BTN_TOOL_RUBBER'),
        #         libevdev.evbit('BTN_STYLUS'),
        #         libevdev.evbit('BTN_STYLUS2'),
        #     ]
        self._device = self._create_device()

    def __repr__(self) -> str:
        return f'{type(self).__name__}(name="{self._name}")'

    @classmethod
    def create(
        cls,
        source_device: SourceDevice,
        properties: Optional[Dict] = None,
    ) -> DestinationDevice:
        return cls(
            source_device.name + ' (Virtual)',
            source_device.id,
            source_device.evbits,
            source_device.absinfo,
            source_device.rep_value,
            source_device.input_properties,
            properties,
        )

    def send_events(self, events: List[libevdev.InputEvent]):
        self._device.send_events(events)

    def _create_device(self):
        raise NotImplementedError('Override me')

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
            'properties': [p.value for p in self._input_properties],
        }

class UinputDestinationDevice(DestinationDevice):
    def _create_device(self) -> libevdev.device.UinputDevice:
        device = libevdev.Device()
        device.name = self._name
        device.id = self._id
        for type_, evbits in self._evbits.items():
            for evbit in evbits:
                if type_ == libevdev.EV_ABS:
                    if evbit not in self._absinfo:
                        log.error(f'evbit not found: {evbit} {self._absinfo}')
                        continue
                    data = self._absinfo[evbit]
                elif type_ == libevdev.EV_REP:
                    data = self._rep_value[evbit]
                else:
                    data = None
                device.enable(evbit, data)

        for p in self._input_properties:
            device.enable(p)

        uinput_device = device.create_uinput_device()
        time.sleep(0.5)
        return uinput_device

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
                    self._send_data(self._get_details_data())
                    self._details_sent = True
                self._send_data(json.dumps({
                    'events': [
                        {'type': e.type.value, 'code': e.code.value, 'value': e.value}
                        for e in events
                    ]
                }).encode('utf-8'))
            def _get_details_data(self) -> bytes:
                return json.dumps({
                    'host': self._host,
                    'vendor': self._details['id']['vendor'],
                    'product': self._details['id']['product'],
                    'data': self._details,
                }).encode('utf-8')
            def _send_data(self, data: bytes):
                try:
                    self._send_data_raw(data)
                except (BrokenPipeError, AttributeError):
                    self._details_sent = False
                    log.info('Created new handle')
                    self._handle = self._create_handle()
                    try:
                        self._send_data_raw(self._get_details_data())
                        self._details_sent = True
                        self._send_data_raw(data)
                    except:
                        pass
            def _send_data_raw(self, data: bytes):
                if self._handle.stdin is None:
                    raise AttributeError
                self._handle.stdin.write(data + b'\n')
                self._handle.stdin.flush()

            def _create_handle(self) -> subprocess.Popen:
                # TODO two-way communication? ACK etc
                handle = subprocess.Popen(
                    self._command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                )
                def _log_stdout(stream):
                    for line in iter(stream.readline, b''):
                        log.info('_SubprocessDevice.STDOUT: ' + line.decode('utf-8', 'ignore'))
                def _log_stderr(stream):
                    for line in iter(stream.readline, b''):
                        log.error('_SubprocessDevice.STDERR: ' + line.decode('utf-8', 'ignore'))
                threading.Thread(target=_log_stdout, args=(handle.stdout,)).start()
                threading.Thread(target=_log_stderr, args=(handle.stderr,)).start()
                return handle
        return _SubprocessDevice(self._properties['command'], self._serialize())

class HidGadgetDestinationDevice(DestinationDevice):
    # TODO
    # https://github.com/siikamiika/hid-emu
    # https://www.kernel.org/doc/Documentation/usb/gadget_hid.txt
    def _create_device(self):
        # TODO mouse
        evdev_key_to_hid_code = {
            libevdev.evbit(k): v for k, v in
            [
                ('KEY_A',                0x04),
                ('KEY_B',                0x05),
                ('KEY_C',                0x06),
                ('KEY_D',                0x07),
                ('KEY_E',                0x08),
                ('KEY_F',                0x09),
                ('KEY_G',                0x0a),
                ('KEY_H',                0x0b),
                ('KEY_I',                0x0c),
                ('KEY_J',                0x0d),
                ('KEY_K',                0x0e),
                ('KEY_L',                0x0f),
                ('KEY_M',                0x10),
                ('KEY_N',                0x11),
                ('KEY_O',                0x12),
                ('KEY_P',                0x13),
                ('KEY_Q',                0x14),
                ('KEY_R',                0x15),
                ('KEY_S',                0x16),
                ('KEY_T',                0x17),
                ('KEY_U',                0x18),
                ('KEY_V',                0x19),
                ('KEY_W',                0x1a),
                ('KEY_X',                0x1b),
                ('KEY_Y',                0x1c),
                ('KEY_Z',                0x1d),
                ('KEY_1',                0x1e),
                ('KEY_2',                0x1f),
                ('KEY_3',                0x20),
                ('KEY_4',                0x21),
                ('KEY_5',                0x22),
                ('KEY_6',                0x23),
                ('KEY_7',                0x24),
                ('KEY_8',                0x25),
                ('KEY_9',                0x26),
                ('KEY_0',                0x27),
                ('KEY_ENTER',            0x28),
                ('KEY_ESC',              0x29),
                ('KEY_BACKSPACE',        0x2a),
                ('KEY_TAB',              0x2b),
                ('KEY_SPACE',            0x2c),
                ('KEY_MINUS',            0x2d),
                ('KEY_EQUAL',            0x2e),
                ('KEY_LEFTBRACE',        0x2f),
                ('KEY_RIGHTBRACE',       0x30),
                ('KEY_BACKSLASH',        0x31),
                ('KEY_BACKSLASH',        0x32),
                ('KEY_SEMICOLON',        0x33),
                ('KEY_APOSTROPHE',       0x34),
                ('KEY_GRAVE',            0x35),
                ('KEY_COMMA',            0x36),
                ('KEY_DOT',              0x37),
                ('KEY_SLASH',            0x38),
                ('KEY_CAPSLOCK',         0x39),
                ('KEY_F1',               0x3a),
                ('KEY_F2',               0x3b),
                ('KEY_F3',               0x3c),
                ('KEY_F4',               0x3d),
                ('KEY_F5',               0x3e),
                ('KEY_F6',               0x3f),
                ('KEY_F7',               0x40),
                ('KEY_F8',               0x41),
                ('KEY_F9',               0x42),
                ('KEY_F10',              0x43),
                ('KEY_F11',              0x44),
                ('KEY_F12',              0x45),
                ('KEY_SYSRQ',            0x46),
                ('KEY_SCROLLLOCK',       0x47),
                ('KEY_PAUSE',            0x48),
                ('KEY_INSERT',           0x49),
                ('KEY_HOME',             0x4a),
                ('KEY_PAGEUP',           0x4b),
                ('KEY_DELETE',           0x4c),
                ('KEY_END',              0x4d),
                ('KEY_PAGEDOWN',         0x4e),
                ('KEY_RIGHT',            0x4f),
                ('KEY_LEFT',             0x50),
                ('KEY_DOWN',             0x51),
                ('KEY_UP',               0x52),
                ('KEY_NUMLOCK',          0x53),
                ('KEY_KPSLASH',          0x54),
                ('KEY_KPASTERISK',       0x55),
                ('KEY_KPMINUS',          0x56),
                ('KEY_KPPLUS',           0x57),
                ('KEY_KPENTER',          0x58),
                ('KEY_KP1',              0x59),
                ('KEY_KP2',              0x5a),
                ('KEY_KP3',              0x5b),
                ('KEY_KP4',              0x5c),
                ('KEY_KP5',              0x5d),
                ('KEY_KP6',              0x5e),
                ('KEY_KP7',              0x5f),
                ('KEY_KP8',              0x60),
                ('KEY_KP9',              0x61),
                ('KEY_KP0',              0x62),
                ('KEY_KPDOT',            0x63),
                ('KEY_102ND',            0x64),
                ('KEY_COMPOSE',          0x65),
                ('KEY_POWER',            0x66),
                ('KEY_KPEQUAL',          0x67),
                ('KEY_F13',              0x68),
                ('KEY_F14',              0x69),
                ('KEY_F15',              0x6a),
                ('KEY_F16',              0x6b),
                ('KEY_F17',              0x6c),
                ('KEY_F18',              0x6d),
                ('KEY_F19',              0x6e),
                ('KEY_F20',              0x6f),
                ('KEY_F21',              0x70),
                ('KEY_F22',              0x71),
                ('KEY_F23',              0x72),
                ('KEY_F24',              0x73),
                ('KEY_OPEN',             0x74),
                ('KEY_HELP',             0x75),
                ('KEY_PROPS',            0x76),
                ('KEY_FRONT',            0x77),
                ('KEY_STOP',             0x78),
                ('KEY_AGAIN',            0x79),
                ('KEY_UNDO',             0x7a),
                ('KEY_CUT',              0x7b),
                ('KEY_COPY',             0x7c),
                ('KEY_PASTE',            0x7d),
                ('KEY_FIND',             0x7e),
                ('KEY_MUTE',             0x7f),
                ('KEY_VOLUMEUP',         0x80),
                ('KEY_VOLUMEDOWN',       0x81),
                ('KEY_KPCOMMA',          0x85),
                ('KEY_RO',               0x87),
                ('KEY_KATAKANAHIRAGANA', 0x88),
                ('KEY_YEN',              0x89),
                ('KEY_HENKAN',           0x8a),
                ('KEY_MUHENKAN',         0x8b),
                ('KEY_KPJPCOMMA',        0x8c),
                ('KEY_HANGEUL',          0x90),
                ('KEY_HANJA',            0x91),
                ('KEY_KATAKANA',         0x92),
                ('KEY_HIRAGANA',         0x93),
                ('KEY_ZENKAKUHANKAKU',   0x94),
                ('KEY_KPLEFTPAREN',      0xb6),
                ('KEY_KPRIGHTPAREN',     0xb7),
                ('KEY_LEFTCTRL',         0xe0),
                ('KEY_LEFTSHIFT',        0xe1),
                ('KEY_LEFTALT',          0xe2),
                ('KEY_LEFTMETA',         0xe3),
                ('KEY_RIGHTCTRL',        0xe4),
                ('KEY_RIGHTSHIFT',       0xe5),
                ('KEY_RIGHTALT',         0xe6),
                ('KEY_RIGHTMETA',        0xe7),
                ('KEY_PLAYPAUSE',        0xe8),
                ('KEY_STOPCD',           0xe9),
                ('KEY_PREVIOUSSONG',     0xea),
                ('KEY_NEXTSONG',         0xeb),
                ('KEY_EJECTCD',          0xec),
                ('KEY_VOLUMEUP',         0xed),
                ('KEY_VOLUMEDOWN',       0xee),
                ('KEY_MUTE',             0xef),
                ('KEY_WWW',              0xf0),
                ('KEY_BACK',             0xf1),
                ('KEY_FORWARD',          0xf2),
                ('KEY_STOP',             0xf3),
                ('KEY_FIND',             0xf4),
                ('KEY_SCROLLUP',         0xf5),
                ('KEY_SCROLLDOWN',       0xf6),
                ('KEY_EDIT',             0xf7),
                ('KEY_SLEEP',            0xf8),
                ('KEY_COFFEE',           0xf9),
                ('KEY_REFRESH',          0xfa),
                ('KEY_CALC',             0xfb),
            ]
        }
        class _HidGadgetDevice:
            _REPORT_ID = 0x01
            _HID_MODIFIER_BEGIN = 0xe0 # left control
            _HID_MODIFIER_END = 0xe7 # right meta
            def __init__(self):
                self._report = bytearray(8)
                self._modifier_byte = memoryview(self._report)[0:1]
                # byte 1 unused
                self._key_bytes = memoryview(self._report)[2:]
            def send_events(self, events: List[libevdev.InputEvent]):
                for event in events:
                    if event.type == libevdev.EV_KEY:
                        hid_code = evdev_key_to_hid_code.get(event.code)
                        if hid_code is None:
                            continue
                        if event.value == 1:
                            self._add_keycode_to_report(hid_code)
                        elif event.value == 0:
                            self._remove_keycode_from_report(hid_code)
                        self._send_report()
                # log.debug(events)
            def _add_keycode_to_report(self, code):
                if self._HID_MODIFIER_BEGIN <= code <= self._HID_MODIFIER_END:
                    self._modifier_byte[0] |= 1 << (code - self._HID_MODIFIER_BEGIN)
                    return
                for i in range(6):
                    if self._key_bytes[i] == code:
                        return
                for i in range(6):
                    if self._key_bytes[i] == 0:
                        self._key_bytes[i] = code
                        return
                # TODO too many keys pressed
            def _remove_keycode_from_report(self, code):
                if self._HID_MODIFIER_BEGIN <= code <= self._HID_MODIFIER_END:
                    self._modifier_byte[0] &= ~(1 << (code - self._HID_MODIFIER_BEGIN))
                    return
                for i in range(6):
                    if self._key_bytes[i] == code:
                        self._key_bytes[i] = 0
            def _send_report(self):
                # TODO mouse report_id 0x02
                with open('/dev/hidg0', 'wb') as f:
                    f.write(bytes(0x01) + self._report)
                log.debug(f'TODO HID report: {bytes([self._REPORT_ID]) + self._report}')
        return _HidGadgetDevice()
