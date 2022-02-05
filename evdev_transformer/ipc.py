import socket
import os
import contextlib
import queue
import threading
from typing import (
    Iterable,
    TextIO,
)
import json

class IpcManager:
    def __init__(self):
        self._queue: queue.Queue[TextIO] = queue.Queue()
        self._sock = self._get_socket()
        threading.Thread(target=self._handle_socket).start()

    def events(self) -> Iterable[TextIO]:
        yield from iter(self._queue.get, None)

    def _get_socket(self) -> socket.socket:
        # bash: "${XDG_RUNTIME_DIR:-/tmp}/evdev-ipc.sock"
        base_path = os.environ.get('XDG_RUNTIME_DIR', '/tmp')
        socket_path = os.path.join(base_path, 'evdev-ipc.sock')
        with contextlib.suppress(FileNotFoundError):
            os.remove(socket_path)
        sock = socket.socket(family=socket.AF_UNIX, type=socket.SOCK_STREAM)
        # restrict access to current user before binding
        os.fchmod(sock.fileno(), 0o600)
        sock.bind(socket_path)
        sock.listen(1)
        return sock

    def _handle_socket(self):
        while True:
            conn, _ = self._sock.accept()
            self._queue.put(conn.makefile())
