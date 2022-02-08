from __future__ import annotations
from typing import (
    List,
    Tuple,
    Dict,
    Optional,
    Iterable
)
import queue
import json
import threading

import libevdev

# TODO replace some validation with https://github.com/agronholm/typeguard

class Transform:
    def __init__(self, properties: Dict):
        self._properties = properties
        self._validate()

    @classmethod
    def from_dict(cls, data: Dict) -> Transform:
        cls_ = {
            'key_remap': KeyRemapTransform,
            'script': ScriptTransform,
        }[data['type']]
        return cls_(data.get('properties', {}))

    def to_dict(self) -> Dict:
        return {
            'type': None,
            'properties': self._properties,
        }

    def _validate(self):
        assert isinstance(self._properties, dict)

class KeyRemapTransform(Transform):
    def to_dict(self) -> Dict:
        d = super().to_dict()
        d['type'] = 'key_remap'
        return d

    def _validate(self):
        assert isinstance(self._properties.get('remaps'), list)
        assert all(bool(libevdev.evbit(m.get(k))) for k in ['source', 'destination'] for m in self._properties['remaps'])

class ScriptTransform(Transform):
    def to_dict(self) -> Dict:
        d = super().to_dict()
        d['type'] = 'script'
        return d

    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('filename'), str)

class Source:
    def __init__(
        self,
        name: str,
        transforms: List[Transform],
        properties: Dict,
    ):
        self._name = name
        self._transforms = transforms
        self._properties = properties
        self._validate()

    @property
    def name(self) -> str:
        return self._name

    @property
    def identifier(self) -> Dict:
        raise NotImplementedError('Override me')

    @classmethod
    def from_dict(cls, data: Dict) -> Source:
        cls_ = {
            'evdev_udev': EvdevUdevSource,
            'evdev_unix_socket': EvdevUnixSocketSource,
        }[data['type']]
        return cls_(
            data['name'],
            [Transform.from_dict(t) for t in data.get('transforms', [])],
            data.get('properties', {}),
        )

    def to_dict(self) -> Dict:
        return {
            'name': self._name,
            'type': None,
            'transforms': [t.to_dict() for t in self._transforms],
            'properties': self._properties,
        }

    def _validate(self):
        assert isinstance(self._name, str)
        assert isinstance(self._properties, dict)

    def __repr__(self):
        return f'{self.__class__.__name__}(name="{self._name}")'

class EvdevUdevSource(Source):
    def to_dict(self) -> Dict:
        d = super().to_dict()
        d['type'] = 'evdev_udev'
        return d

    @property
    def identifier(self):
        return self._properties['udev']

    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('udev'), dict)
        assert all(isinstance(v, str) for v in self._properties['udev'].values())

class EvdevUnixSocketSource(Source):
    def to_dict(self) -> Dict:
        d = super().to_dict()
        d['type'] = 'evdev_unix_socket'
        return d

    @property
    def identifier(self):
        return {
            'host': self._properties['host'],
            'vendor': self._properties['vendor'],
            'product': self._properties['product'],
        }

    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('host'), str)
        assert isinstance(self._properties.get('vendor'), int)
        assert isinstance(self._properties.get('product'), int)

class SourceGroup:
    def __init__(
        self,
        name: str,
        sources: List[str],
    ):
        self._name = name
        self._sources = sources
        self._validate()

    @property
    def name(self) -> str:
        return self._name

    @property
    def sources(self) -> List[str]:
        return self._sources

    @classmethod
    def from_dict(cls, data: Dict) -> SourceGroup:
        return cls(
            data['name'],
            data['sources'],
        )

    def to_dict(self) -> Dict:
        return {
            'name': self._name,
            'sources': self._sources,
        }

    def _validate(self):
        assert isinstance(self._name, str)
        assert all(isinstance(s, str) for s in self._sources)

    def __repr__(self):
        return f'SourceGroup(name="{self._name}", sources={json.dumps(self._sources)})'

class Destination:
    def __init__(
        self,
        name: str,
        transforms: List[Transform],
        properties: Dict,
    ):
        self._name = name
        self._transforms = transforms
        self._properties = properties
        self._validate()

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def from_dict(cls, data) -> Destination:
        cls_ = {
            'uinput': UinputDestination,
            'subprocess': SubprocessDestination,
        }[data['type']]
        return cls_(
            data['name'],
            [Transform.from_dict(t) for t in data.get('transforms', [])],
            data.get('properties', {}),
        )

    def to_dict(self) -> Dict:
        return {
            'name': self._name,
            'type': None,
            'transforms': [t.to_dict() for t in self._transforms],
            'properties': self._properties,
        }

    def _validate(self):
        assert isinstance(self._name, str)
        assert isinstance(self._properties, dict)

    def __repr__(self):
        return f'{self.__class__.__name__}(name="{self._name}")'

class UinputDestination(Destination):
    def to_dict(self) -> Dict:
        d = super().to_dict()
        d['type'] = 'uinput'
        return d

class SubprocessDestination(Destination):
    def to_dict(self):
        d = super().to_dict()
        d['type'] = 'subprocess'
        return d

    @property
    def command(self) -> str:
        return self._properties['command']

    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('command'), str)

class Activator:
    def __init__(self, properties: Dict):
        self._properties = properties
        self._validate()

    def __eq__(self, other) -> bool:
        return self.to_dict() == other.to_dict()

    @classmethod
    def from_dict(cls, data: Dict) -> Activator:
        cls_ = {
            'script': ScriptActivator,
            'hotkey': HotkeyActivator,
        }[data['type']]
        return cls_(data.get('properties', {}))

    def to_dict(self) -> Dict:
        return {
            'type': None,
            'properties': self._properties,
        }

    def _validate(self):
        assert isinstance(self._properties, dict)

class ScriptActivator(Activator):
    def to_dict(self) -> Dict:
        d = super().to_dict()
        d['type'] = 'script'
        return d

    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('filename'), str)

class HotkeyActivator(Activator):
    def to_dict(self) -> Dict:
        d = super().to_dict()
        d['type'] = 'hotkey'
        return d

    @property
    def key(self) -> str:
        return self._properties['hotkey']['key']

    @property
    def modifiers(self) -> List[str]:
        return self._properties['hotkey']['modifiers']

    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('hotkey'), dict)
        assert bool(libevdev.evbit(self._properties['hotkey'].get('key')))
        assert isinstance(self._properties['hotkey'].get('modifiers'), list)
        assert all(bool(libevdev.evbit(m)) for m in self._properties['hotkey']['modifiers'])

class Link:
    def __init__(
        self,
        source_group: str,
        destination: str,
        activators: List[Activator],
    ):
        self._source_group = source_group
        self._destination = destination
        self._activators = activators
        self._validate()

    @property
    def source_group(self) -> str:
        return self._source_group

    @property
    def destination(self) -> str:
        return self._destination

    @property
    def activators(self) -> List[Activator]:
        return self._activators

    @classmethod
    def from_dict(cls, data) -> Link:
        return cls(
            data['source_group'],
            data['destination'],
            [Activator.from_dict(a) for a in data.get('activators', [])],
        )

    def to_dict(self) -> Dict:
        return {
            'source_group': self._source_group,
            'destination': self._destination,
            'activators': [a.to_dict() for a in self._activators],
        }

    def _validate(self):
        assert isinstance(self._source_group, str)
        assert isinstance(self._destination, str)
        activators = []
        for activator in self._activators:
            assert activator not in activators
            activators.append(activator)

    def __repr__(self):
        return f'Link(source_group="{self._source_group}" destination="{self._destination}")'

class Config:
    _newest_version = 1

    def __init__(
        self,
        version: int,
        sources: List[Source],
        source_groups: List[SourceGroup],
        destinations: List[Destination],
        links: List[Link],
    ):
        self._version = version
        self._sources = sources
        self._source_groups = source_groups
        self._destinations = destinations
        self._links = links
        self._validate()

    @property
    def version(self) -> int:
        return self._version

    @property
    def sources(self) -> List[Source]:
        return self._sources

    @property
    def source_groups(self) -> List[SourceGroup]:
        return self._source_groups

    @property
    def destinations(self) -> List[Destination]:
        return self._destinations

    @property
    def links(self) -> List[Link]:
        return self._links

    @classmethod
    def from_dict(cls, data: Dict) -> Config:
        return cls(
            data['config_version'],
            [Source.from_dict(s) for s in data['sources']],
            [SourceGroup.from_dict(s) for s in data['source_groups']],
            [Destination.from_dict(d) for d in data['destinations']],
            [Link.from_dict(l) for l in data['links']],
        )

    def to_dict(self) -> Dict:
        return {
            'config_version': self._version,
            'sources': [s.to_dict() for s in self._sources],
            'source_groups': [s.to_dict() for s in self._source_groups],
            'destinations': [d.to_dict() for d in self._destinations],
            'links': [l.to_dict() for l in self._links],
        }

    def _validate(self):
        # TODO config version migrations
        if self._version != self._newest_version:
            raise Exception(f'Invalid version: config version {self._version} != newest version {self._newest_version}')
        # sources
        assert len(set(s.name for s in self._sources)) == len(self._sources)
        # source groups
        for source_group in self._source_groups:
            for source_group2 in self._source_groups:
                if source_group2 == source_group:
                    continue
                if set(source_group.sources) & set(source_group2.sources):
                    raise Exception('Overlapping source groups')
                if source_group.name == source_group2.name:
                    raise Exception('Duplicate name for source groups')
            assert len([s for s in self._sources if s.name in source_group.sources]) == len(source_group.sources)
        # links
        assert len(set((l.source_group, l.destination) for l in self._links)) == len(self._links)
        for link in self._links:
            assert len([s for s in self._source_groups if s.name == link.source_group]) == 1
            assert len([d for d in self._destinations if d.name == link.destination]) == 1
        # destinations
        assert len(set(d.name for d in self._destinations)) == len(self._destinations)

class ConfigManager:
    def __init__(self, config_path):
        self._config_path = config_path
        self._event_queue = queue.Queue()
        self._current_links: List[Link] = []
        self._config = self._load_config()
        self._lock = threading.Lock()
        self._init_state()

    @property
    def source_groups(self) -> List[SourceGroup]:
        return self._config.source_groups

    def get_current_links(self) -> Iterable[Tuple[Link, List[Source], Destination]]:
        for link in self._current_links:
            source_group = [s for s in self._config.source_groups if s.name == link.source_group][0]
            yield (
                link,
                [s for s in self._config.sources if s.name in source_group.sources],
                [d for d in self._config.destinations if d.name == link.destination][0],
            )

    def events(self) -> Iterable[Dict]: # TODO event class
        yield from iter(self._event_queue.get, None)

    def activate_next_link(
        self,
        source_group: str,
        activator: Optional[Activator] = None,
    ):
        with self._lock:
            current_link = None
            for link in self._current_links:
                if link.source_group == source_group:
                    current_link = link
                    break
            else:
                raise Exception('No active link for source group')
            matches = [
                l for l in self._config.links
                if l.source_group == source_group and (
                    activator is None
                    or activator in l.activators
                )
            ]
            if not matches:
                raise Exception('No matches')
            if current_link in matches:
                new_idx = (matches.index(current_link) + 1) % len(matches)
            else:
                new_idx = 0
            new_link = matches[new_idx]
            self._event_queue.put({'type': 'remove', 'object': current_link})
            self._current_links[self._current_links.index(current_link)] = new_link
            self._event_queue.put({'type': 'add', 'object': new_link})

    def _load_config(self) -> Config:
        with open(self._config_path) as f:
            return Config.from_dict(json.load(f))

    def _reload_config(self):
        # TODO diff (add, remove) when reloading config
        # old_config = self._config
        # with open(self._config_path) as f:
        #     new_config = Config.from_dict(json.load(f))
        raise NotImplementedError('Config reload not implemented')

    def _init_state(self):
        for source in self._config.sources:
            self._event_queue.put({'type': 'add', 'object': source})
        for source_group in self._config.source_groups:
            self._event_queue.put({'type': 'add', 'object': source_group})
        for destination in self._config.destinations:
            self._event_queue.put({'type': 'add', 'object': destination})
        seen_source_groups = set()
        for link in self._config.links:
            if link.source_group in seen_source_groups:
                continue
            seen_source_groups.add(link.source_group)
            self._current_links.append(link)
            self._event_queue.put({'type': 'add', 'object': link})
