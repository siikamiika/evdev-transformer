from __future__ import annotations
from typing import (
    List,
    Dict
)

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

class Activator:
    def __init__(self, properties: Dict):
        self._properties = properties
        self._validate()

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

    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('hotkey'), dict)
        assert isinstance(self._properties.get('modifiers'), list)
        assert all(bool(libevdev.evbit(m)) for m in self._properties['modifiers'])

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

class EvdevUdevSource(Source):
    def to_dict(self) -> Dict:
        d = super().to_dict()
        d['type'] = 'evdev_udev'
        return d

    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('udev'), dict)
        assert all(isinstance(v, str) for v in self._properties['udev'].values())

class EvdevUnixSocketSource(Source):
    def to_dict(self) -> Dict:
        d = super().to_dict()
        d['type'] = 'evdev_unix_socket'
        return d

    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('socket_name'), str)
        assert isinstance(self._properties.get('evdev_id'), dict)
        assert all(isinstance(self._properties['evdev_id'][k], int) for k in ['vendor', 'product'])

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
            'ssh_evdev_unix_socket': SshEvdevUnixSocketDestination,
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

class UinputDestination(Destination):
    def to_dict(self) -> Dict:
        d = super().to_dict()
        d['type'] = 'uinput'
        return d

class SshEvdevUnixSocketDestination(Destination):
    def to_dict(self):
        d = super().to_dict()
        d['type'] = 'ssh_evdev_unix_socket'
        return d

    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('socket_name'), str)
        assert isinstance(self._properties.get('host'), str)
        assert isinstance(self._properties.get('username'), str)

class Link:
    def __init__(
        self,
        source_group: SourceGroup,
        destination: Destination,
        activators: List[Activator],
    ):
        self._source_group = source_group
        self._destination = destination
        self._activators = activators
        self._validate()

    @property
    def source_group(self):
        return self._source_group

    @property
    def destination(self):
        return self._destination

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

class Config:
    _newest_version = 1

    def __init__(
        self,
        version: int,
        sources: List[Source],
        source_groups: List[SourceGroup],
        links: List[Link],
        destinations: List[Destination],
    ):
        self._version = version
        self._sources = sources
        self._source_groups = source_groups
        self._links = links
        self._destinations = destinations
        self._validate()

    @classmethod
    def from_dict(cls, data: Dict) -> Config:
        return cls(
            data['config_version'],
            [Source.from_dict(s) for s in data['sources']],
            [SourceGroup.from_dict(s) for s in data['source_groups']],
            [Link.from_dict(l) for l in data['links']],
            [Destination.from_dict(d) for d in data['destinations']],
        )

    def to_dict(self) -> Dict:
        return {
            'version': self._version,
            'sources': [s.to_dict() for s in self._sources],
            'source_groups': [s.to_dict() for s in self._source_groups],
            'links': [l.to_dict() for l in self._links],
            'destinations': [d.to_dict() for d in self._destinations],
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
