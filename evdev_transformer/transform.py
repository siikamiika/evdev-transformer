from __future__ import annotations
from typing import (
    Set,
    Tuple,
    Callable,
    Iterable,
)
import os
import pydoc

import libevdev

from .config import (
    Transform,
    KeyRemapTransform,
    ScriptTransform,
)
from . import log

class EventTransform:
    def __init__(
        self,
        input_codes: Set[libevdev.EventCode],
        # TODO use output_codes to extend destination device codes
        output_codes: Set[libevdev.EventCode],
        transform_event_fn: Callable[[libevdev.InputEvent], Iterable[libevdev.InputEvent]],
    ):
        self._input_codes = input_codes
        self._output_codes = output_codes
        self._transform_event_fn = transform_event_fn

    @classmethod
    def from_config(cls, transform_config: Transform) -> EventTransform:
        if isinstance(transform_config, KeyRemapTransform):
            return KeyRemapEventTransform.from_config(transform_config)
        elif isinstance(transform_config, ScriptTransform):
            return ScriptEventTransform.from_config(transform_config)
        raise NotImplementedError

    def matches_event(self, event: libevdev.InputEvent) -> bool:
        return event.code in self._input_codes

    def transform_event(self, event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
        yield from self._transform_event_fn(event)

class KeyRemapEventTransform(EventTransform):
    @classmethod
    def from_config(cls, transform_config: KeyRemapTransform) -> KeyRemapEventTransform:
        input_codes = set()
        output_codes = set()
        event_map = {}
        for source, destination in transform_config.mapping.items():
            source_code = libevdev.evbit(source)
            destination_code = libevdev.evbit(destination)
            input_codes.add(source_code)
            output_codes.add(destination_code)
            event_map[source_code] = destination_code
        def _transform_event(event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
            yield libevdev.InputEvent(event_map[event.code], event.value)
        return cls(input_codes, output_codes, _transform_event)

class ScriptEventTransform(EventTransform):
    @classmethod
    def from_config(cls, transform_config: ScriptTransform) -> ScriptEventTransform:
        script_path = os.path.expanduser(transform_config.filename)
        script = pydoc.importfile(script_path)
        res: Tuple[Set, Set, Callable] = script.run(log)
        return cls(*res)
