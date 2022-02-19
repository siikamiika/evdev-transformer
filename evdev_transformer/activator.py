from __future__ import annotations
from typing import (
    Callable,
    Iterable,
)

import libevdev

from .config import (
    Activator,
    ScriptActivator,
    HotkeyActivator,
)

class DeviceLinkActivator:
    def __init__(
        self,
        match_fn: Callable[[libevdev.InputEvent], bool],
        activate_fn: Callable,
    ):
        self._match_fn = match_fn
        self._activate_fn = activate_fn

    @classmethod
    def create(
        cls,
        activator_config: Activator,
        has_pressed_keys_fn: Callable[[Iterable[libevdev.EventCode]], bool],
        activate_fn: Callable,
    ) -> DeviceLinkActivator:
        if isinstance(activator_config, HotkeyActivator):
            return HotkeyDeviceLinkActivator.create(activator_config, has_pressed_keys_fn, activate_fn)
        raise NotImplementedError

    def matches_event(self, event: libevdev.InputEvent) -> bool:
        return self._match_fn(event)

    def activate(self):
        self._activate_fn()

class HotkeyDeviceLinkActivator(DeviceLinkActivator):
    @classmethod
    def create(
        cls,
        activator_config: HotkeyActivator,
        has_pressed_keys_fn: Callable[[Iterable[libevdev.EventCode]], bool],
        activate_fn: Callable,
    ) -> HotkeyDeviceLinkActivator:
        return cls(
            lambda e: (
                e.code == activator_config.key
                and e.value == 1
                and has_pressed_keys_fn(activator_config.modifiers)
            ),
            activate_fn,
        )
