import logging
import sys

_FORMAT = '{asctime} {name}.{levelname} {filename}:{lineno} ({funcName}) [{threadName}]: {message}'
_LOGGER = None

def init(logger_name, log_level_name):
    global _LOGGER
    if _LOGGER is not None:
        raise Exception('Logger is already initialized')
    _LOGGER = logging.getLogger(logger_name)
    log_level = logging.getLevelName(log_level_name.upper())
    assert isinstance(log_level, int)
    _LOGGER.setLevel(log_level)

    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(fmt=_FORMAT, style='{')
    handler.setFormatter(formatter)
    _LOGGER.addHandler(handler)

def _log(level, *args, **kwargs):
    if _LOGGER is None:
        raise Exception('Logger not initialized')
    # call _LOGGER.debug(...) etc. and fix stack level to get the correct caller
    # outside of this log module
    getattr(_LOGGER, level)(*args, **kwargs, stacklevel=3)

def debug(*args, **kwargs):
    _log('debug', *args, **kwargs)

def info(*args, **kwargs):
    _log('info', *args, **kwargs)

def warning(*args, **kwargs):
    _log('warning', *args, **kwargs)

def error(*args, **kwargs):
    _log('error', *args, **kwargs)

def critical(*args, **kwargs):
    _log('critical', *args, **kwargs)
