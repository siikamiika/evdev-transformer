import atexit

_cleanup_tasks = []
def _handle_exit():
    for task in _cleanup_tasks:
        task()
atexit.register(_handle_exit)

def add_cleanup_task(task):
    _cleanup_tasks.append(task)
