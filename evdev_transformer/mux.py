import queue
import threading

class DeviceMuxer:
    def __init__(self):
        self._event_queue = queue.Queue()

    def events(self):
        while True:
            yield self._event_queue.get()

    def add_device(self, device):
        def _reader():
            for event in device.events():
                self._event_queue.put((device, event))
        threading.Thread(target=_reader).start()
