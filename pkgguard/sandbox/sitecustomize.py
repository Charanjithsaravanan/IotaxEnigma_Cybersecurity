"""Low-level Python runtime telemetry for the honeypot."""

import json
import os
import sys
import traceback
from typing import Any

_LOG = os.environ.get("SANDBOX_RUNTIME_LOG", "/logs/runtime.jsonl")
_INTERNAL = False


def _write(event: str, **fields: Any) -> None:
    global _INTERNAL
    if _INTERNAL:
        return
    _INTERNAL = True
    try:
        with open(_LOG, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"event": event, **fields}, sort_keys=True) + "\n")
    except OSError:
        pass
    finally:
        _INTERNAL = False


_environ_type = type(os.environ)
_original_getitem = _environ_type.__getitem__
_original_get = _environ_type.get


def _getitem(self: Any, key: str) -> str:
    if _package_context():
        _write("env_read", key=str(key))
    return _original_getitem(self, key)


def _get(self: Any, key: str, default: Any = None) -> Any:
    if _package_context():
        _write("env_read", key=str(key))
    return _original_get(self, key, default)


_environ_type.__getitem__ = _getitem
_environ_type.get = _get


def _audit(event: str, args: tuple[Any, ...]) -> None:
    if event == "socket.getaddrinfo" and args:
        _write("dns_lookup", host=str(args[0]))
    elif event == "socket.connect" and len(args) > 1:
        _write("socket_connect", address=repr(args[1]))
    elif event == "subprocess.Popen" and args:
        command = args[0]
        if isinstance(command, (list, tuple)):
            command = " ".join(str(part) for part in command)
        _write("subprocess", command=str(command))
    elif event.startswith("urllib."):
        _write("urllib", event=event)


try:
    sys.addaudithook(_audit)
except (AttributeError, RuntimeError):
    pass


def _package_context() -> bool:
    """Avoid attributing pip/setuptools' environment discovery to the package."""
    ignored = ("/opt/sandbox-hooks/", "/usr/lib/python", "/usr/local/lib/python", "/usr/bin/")
    for frame in traceback.extract_stack()[:-1]:
        filename = frame.filename
        if filename.startswith("/") and not filename.startswith(ignored):
            return True
    return False