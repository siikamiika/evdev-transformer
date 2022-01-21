import libinput

class LibinputTouchpadEventSource:
    def __init__(self, libevdev_device):
        self._libevdev_device = libevdev_device
        (
            self._libinput,
            self._libinput_device
        ) = self._create_libinput_device()

    def events(self):
        yield from self._libinput.events

    def _create_libinput_device(self):
        li = libinput.LibInput(context_type=libinput.ContextType.PATH)
        device = li.add_device(self._libevdev_device.fd.name)
        device.config.tap.set_button_map(libinput.TapButtonMap.LRM)
        device.config.click.set_method(libinput.ClickMethod.CLICKFINGER)
        return li, device
