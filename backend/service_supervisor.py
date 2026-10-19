"""Supervise the API and explicit expiry process on the existing demo service."""
import json
import signal
import subprocess
from threading import Event


def supervise(commands, stop=None, grace_seconds=10, poll_seconds=0.5, install_signals=True):
    stop = stop or Event()
    children, previous = {}, {}
    exit_code = 0
    try:
        if install_signals:
            for signum in (signal.SIGTERM, signal.SIGINT):
                previous[signum] = signal.signal(signum, lambda *_: stop.set())
        for name, command in commands.items():
            children[name] = subprocess.Popen(command)
            print(json.dumps({'event':'service.child_started','process':name}), flush=True)
        while not stop.wait(poll_seconds):
            for name, child in children.items():
                code = child.poll()
                if code is not None:
                    print(json.dumps({'event':'service.child_exited','process':name,'exitCode':code}), flush=True)
                    exit_code = code if code and code > 0 else 1
                    stop.set()
                    break
    finally:
        for child in children.values():
            if child.poll() is None:
                child.terminate()
        for child in children.values():
            try:
                child.wait(timeout=grace_seconds)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=grace_seconds)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    return exit_code
