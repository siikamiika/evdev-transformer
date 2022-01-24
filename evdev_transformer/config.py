import libevdev

class Config:
    _newest_version = 1

    def __init__(self, version, sources, source_groups, links, destinations):
        self._version = version
        self._sources = sources
        self._source_groups = source_groups
        self._links = links
        self._destinations = destinations
        self._validate()

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['config_version'],
            [Source.from_dict(s) for s in data['sources']],
            [SourceGroup.from_dict(s) for s in data['source_groups']],
            [Link.from_dict(l) for l in data['links']],
            [Destination.from_dict(d) for d in data['destinations']],
        )

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

class Source:
    def __init__(self, name, transforms, properties):
        self._name = name
        self._transforms = transforms
        self._properties = properties
        self._validate()

    @property
    def name(self):
        return self._name

    @classmethod
    def from_dict(cls, data):
        cls_ = {
            'evdev_udev': EvdevUdevSource,
            'evdev_unix_socket': EvdevUnixSocketSource,
        }[data['type']]
        return cls_(
            data['name'],
            [Transform.from_dict(t) for t in data.get('transforms', [])],
            data.get('properties', {}),
        )

    def _validate(self):
        assert isinstance(self._name, str)
        assert isinstance(self._properties, dict)

class EvdevUdevSource(Source):
    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('udev'), dict)
        assert all(isinstance(v, str) for v in self._properties['udev'].values())

class EvdevUnixSocketSource(Source):
    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('socket_name'), str)
        assert isinstance(self._properties.get('evdev_id'), dict)
        assert all(isinstance(self._properties['evdev_id'][k], int) for k in ['vendor', 'product'])

class SourceGroup:
    def __init__(self, name, sources):
        self._name = name
        self._sources = sources
        self._validate()

    @property
    def name(self):
        return self._name

    @property
    def sources(self):
        return self._sources

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['name'],
            data['sources'],
        )

    def _validate(self):
        assert isinstance(self._name, str)
        assert all(isinstance(s, str) for s in self._sources)

class Link:
    def __init__(self, source_group, destination, activators):
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
    def from_dict(cls, data):
        return cls(
            data['source_group'],
            data['destination'],
            [Activator.from_dict(a) for a in data.get('activators', [])],
        )

    def _validate(self):
        assert isinstance(self._source_group, str)
        assert isinstance(self._destination, str)

class Destination:
    def __init__(self, name, transforms, properties):
        self._name = name
        self._transforms = transforms
        self._properties = properties
        self._validate()

    @property
    def name(self):
        return self._name

    @classmethod
    def from_dict(cls, data):
        cls_ = {
            'uinput': UinputDestination,
            'ssh_evdev_unix_socket': SshEvdevUnixSocketDestination,
        }[data['type']]
        return cls_(
            data['name'],
            [Transform.from_dict(t) for t in data.get('transforms', [])],
            data.get('properties', {}),
        )

    def _validate(self):
        assert isinstance(self._name, str)
        assert isinstance(self._properties, dict)

class UinputDestination(Destination):
    pass

class SshEvdevUnixSocketDestination(Destination):
    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('socket_name'), str)
        assert isinstance(self._properties.get('host'), str)
        assert isinstance(self._properties.get('username'), str)

class Transform:
    def __init__(self, properties):
        self._properties = properties
        self._validate()

    @classmethod
    def from_dict(cls, data):
        cls_ = {
            'key_remap': KeyRemapTransform,
            'script': ScriptTransform,
        }[data['type']]
        return cls_(data.get('properties', {}))

    def _validate(self):
        assert isinstance(self._properties, dict)

class KeyRemapTransform(Transform):
    def _validate(self):
        assert isinstance(self._properties.get('remaps'), list)
        assert all(bool(libevdev.evbit(m.get(k))) for k in ['source', 'destination'] for m in self._properties['remaps'])

class ScriptTransform(Transform):
    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('filename'), str)

class Activator:
    def __init__(self, properties):
        self._properties = properties
        self._validate()

    @classmethod
    def from_dict(cls, data):
        cls_ = {
            'script': ScriptActivator,
            'hotkey': HotkeyActivator,
        }[data['type']]
        return cls_(data.get('properties', {}))

    def _validate(self):
        assert isinstance(self._properties, dict)

class ScriptActivator(Activator):
    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('filename'), str)

class HotkeyActivator(Activator):
    def _validate(self):
        super()._validate()
        assert isinstance(self._properties.get('hotkey'), dict)
        assert isinstance(self._properties.get('modifiers'), list)
        assert all(bool(libevdev.evbit(m)) for m in self._properties['modifiers'])
