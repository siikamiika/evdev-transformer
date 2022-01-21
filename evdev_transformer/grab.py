import json
import subprocess
import os

from .cleanup import add_cleanup_task

class DeviceGrabManager:
    def __init__(self, libevdev_device, udev_device):
        self._libevdev_device = libevdev_device
        self._udev_device = udev_device

    def grab(self):
        if self._udev_device.get('ID_INPUT_TOUCHPAD'):
            # don't grab the evdev device itself because otherwise libinput wouldn't get any events
            if os.environ.get('SWAYSOCK'):
                self._sway_grab_touchpad(self._libevdev_device)
        else:
            self._libevdev_device.grab()

    def _sway_get_touchpad_identifier(self, device):
        sway_inputs = json.loads(subprocess.run(['swaymsg', '-t', 'get_inputs'], stdout=subprocess.PIPE).stdout)
        for sway_input in sway_inputs:
            if all(device.id[k] == sway_input[k] for k in ['vendor', 'product']):
                if sway_input['type'] == 'touchpad':
                    return sway_input['identifier']
        return None

    def _sway_grab_touchpad(self, device):
        sway_input_identifier = self._sway_get_touchpad_identifier(device)
        if sway_input_identifier:
            subprocess.run(['swaymsg', 'input', sway_input_identifier, 'events', 'disabled'])
            add_cleanup_task(lambda: subprocess.run(['swaymsg', 'input', sway_input_identifier, 'events', 'enabled']))
