import libevdev

class EvdevWrapper:
    _uinput_cache = {}
    def __init__(self, libevdev_device):
        self._device = libevdev_device
        self._pressed_keys = set()
        self._event_loop_stopped = []
        self._buffer = []

    def get_fd_name(self):
        return self._device.fd.name

    def has_pressed_keys(self, keys):
        if not isinstance(keys, set):
            keys = set(keys)
        return len(keys) == len(self._pressed_keys & keys)

    def get_pressed_keys(self):
        return self._pressed_keys

    def create_uinput_device(self):
        devname = self.get_fd_name()
        if devname in self._uinput_cache:
            return self._uinput_cache[devname]
        dev = libevdev.Device(open(devname, 'rb'))
        dev.name = (dev.name or 'Input Device') + ' (Virtual)'
        uinput_device = dev.create_uinput_device()
        self._uinput_cache[devname] = uinput_device
        return uinput_device

    def release(self):
        self._device.ungrab()
        self._event_loop_stopped = [True for _ in self._event_loop_stopped]

    def events(self):
        self._device.grab()
        loop_id = len(self._event_loop_stopped)
        self._event_loop_stopped.append(False)
        while True:
            try:
                for event in self._device.events():
                    if self._event_loop_stopped[loop_id]:
                        break
                    yield from self._handle_event(event)
            except libevdev.device.EventsDroppedException:
                for event in self._device.sync():
                    yield from self._handle_event(event)

    def _handle_event(self, event):
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
