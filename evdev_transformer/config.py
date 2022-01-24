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
        raise NotImplementedError

class Source:
    def __init__(self, name, transforms, properties):
        self._name = name
        self._transforms = transforms
        self._properties = properties
        self._validate()

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
        raise NotImplementedError

class EvdevUdevSource(Source):
    pass

class EvdevUnixSocketSource(Source):
    pass

class SourceGroup:
    def __init__(self, name, sources):
        self._name = name
        self._sources = sources
        self._validate()

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['name'],
            data['sources'],
        )

    def _validate(self):
        raise NotImplementedError

class Link:
    def __init__(self, source_group, destination, activators):
        self._source_group = source_group
        self._destination = destination
        self._activators = activators
        self._validate()

    @classmethod
    def from_dict(cls, data):
        return cls(
            data['source_group'],
            data['destination'],
            [Activator.from_dict(a) for a in data.get('activators', [])],
        )

    def _validate(self):
        raise NotImplementedError

class Destination:
    def __init__(self, name, transforms, properties):
        self._name = name
        self._transforms = transforms
        self._properties = properties
        self._validate()

    @classmethod
    def from_dict(cls, data):
        cls_ = {
            'uinput': UinputDestination,
            'ssh_evdev_unix_socket': SshEvdevUnixSocketDestination,
        }[data['type']]
        return cls_(
            data['name'],
            data['transforms'],
            data.get('properties', {}),
        )

    def _validate(self):
        raise NotImplementedError

class UinputDestination(Destination):
    pass

class SshEvdevUnixSocketDestination(Destination):
    pass

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
        raise NotImplementedError

class KeyRemapTransform(Transform):
    pass

class ScriptTransform(Transform):
    pass

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
        raise NotImplementedError

class ScriptActivator(Activator):
    pass

class HotkeyActivator(Activator):
    pass
