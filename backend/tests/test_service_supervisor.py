"""Real child process lifecycle tests; no deployment credentials or DB writes."""
import importlib.util
from pathlib import Path
import subprocess
import sys
from threading import Event, Timer
import pytest
import service_supervisor


@pytest.mark.parametrize('critical', ['api','payment-expiry'])
def test_critical_child_failure_stops_its_peer(monkeypatch, critical):
    original, children = subprocess.Popen, []
    def launch(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(service_supervisor.subprocess,'Popen',launch)
    commands = {name:[sys.executable,'-c','import sys;sys.exit(7)' if name==critical else 'import time;time.sleep(60)']
        for name in ('api','payment-expiry')}
    code=service_supervisor.supervise(commands,grace_seconds=2,poll_seconds=0.02,install_signals=False)
    assert code==7 and len(children)==2 and all(child.poll() is not None for child in children)


def test_shutdown_request_stops_both_children(monkeypatch):
    original, children = subprocess.Popen, []
    def launch(*args, **kwargs):
        child=original(*args, **kwargs);children.append(child);return child
    monkeypatch.setattr(service_supervisor.subprocess,'Popen',launch)
    stop=Event();timer=Timer(0.2,stop.set);timer.start()
    try:
        assert service_supervisor.supervise({name:[sys.executable,'-c','import time;time.sleep(60)']
            for name in ('api','payment-expiry')},stop=stop,grace_seconds=2,install_signals=False)==0
        assert all(child.poll() is not None for child in children)
    finally: timer.cancel()


def test_expiry_cutover_requires_timezone():
    path=Path(__file__).resolve().parents[2]/'scripts/payment/expire_pending.py'
    spec=importlib.util.spec_from_file_location('expiry_cutover_test',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.parse_cutover('') is None
    assert module.parse_cutover('2026-10-19T19:00:00+07:00')==module.parse_cutover('2026-10-19T12:00:00Z')
    with pytest.raises(Exception,match='timezone'): module.parse_cutover('2026-10-19T12:00:00')


@pytest.mark.parametrize('creation_enabled,worker_flag', [(False,'true'),(True,'false')])
def test_entrypoint_keeps_worker_for_pending_holds_even_if_creation_disabled(monkeypatch, creation_enabled, worker_flag):
    import serve
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.setenv('PAYMENT_EXPIRY_WORKER_ENABLED',worker_flag)
    monkeypatch.setattr(sys,'argv',['serve.py'])
    monkeypatch.setattr(serve,'load_config',lambda: {'VNPAY_ENABLED':creation_enabled})
    captured=[]
    monkeypatch.setattr(serve,'supervise',lambda commands: captured.append(commands) or 0)
    with pytest.raises(SystemExit) as result: serve.main()
    assert result.value.code==0 and set(captured[0])=={'api','payment-expiry'}
