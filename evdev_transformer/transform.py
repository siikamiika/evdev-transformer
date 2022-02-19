from __future__ import annotations
from typing import (
    List,
    Callable,
    Iterable,
)

import libevdev

from .config import (
    Transform,
    KeyRemapTransform,
    ScriptTransform,
)

class EventTransform:
    def __init__(
        self,
        input_codes: List[libevdev.EventCode],
        # TODO use output_codes to extend destination device codes
        output_codes: List[libevdev.EventCode],
        transform_event_fn: Callable[[libevdev.InputEvent], Iterable[libevdev.InputEvent]],
    ):
        self._input_codes = input_codes
        self._output_codes = output_codes
        self._transform_event_fn = transform_event_fn

    @classmethod
    def from_config(cls, transform_config: Transform) -> EventTransform:
        if isinstance(transform_config, KeyRemapTransform):
            return KeyRemapEventTransform.from_config(transform_config)
        raise NotImplementedError

    def matches_event(self, event: libevdev.InputEvent) -> bool:
        return event.code in self._input_codes

    def transform_event(self, event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
        yield from self._transform_event_fn(event)

class KeyRemapEventTransform(EventTransform):
    @classmethod
    def from_config(cls, transform_config: KeyRemapTransform) -> KeyRemapEventTransform:
        # TODO make KeyRemapTransform config support multiple mappings again
        input_codes = [libevdev.evbit(transform_config.source)]
        output_codes = [libevdev.evbit(transform_config.destination)]
        event_map = {input_codes[0]: output_codes[0]}
        def _transform_event(event: libevdev.InputEvent) -> Iterable[libevdev.InputEvent]:
            yield libevdev.InputEvent(event_map[event.code], event.value)
        return cls(input_codes, output_codes, _transform_event)
