"""Start the owned local demo copy without editing .env or existing databases.

Private runtime.json provides existing Python/mongod paths and a local JWT key.
No process is killed, no database is reset, and VNPAY stays disabled locally.
"""
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local/defense-final'


def listening(port):
    with socket.socket() as sock:
        return sock.connect_ex(('127.0.0.1', port)) == 0


def start():
    cfg = json.loads((PRIVATE / 'runtime.json').read_text(encoding='utf-8'))
    ownership = json.loads((PRIVATE / 'local-copy-ownership.json').read_text(encoding='utf-8'))
    assert ownership == {'project': str(ROOT), 'destination': 'ecommerce_defense', 'endpoint': '127.0.0.1:27017/rs0'}
    data = (ROOT / '.local/review/mongo-data').resolve(strict=True)
    assert data.is_relative_to(ROOT / '.local')
    pids = {}
    def spawn(name, command, env=None, cwd=ROOT):
        with (PRIVATE / (name + '-stdout.log')).open('ab') as out, (PRIVATE / (name + '-stderr.log')).open('ab') as err:
            proc = subprocess.Popen(command, cwd=cwd, env=env, stdout=out, stderr=err,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        pids[name] = proc.pid
        (PRIVATE / 'started-processes.json').write_text(json.dumps(pids, indent=2), encoding='utf-8')
    if not listening(27017):
        spawn('mongo', [cfg['mongod'], '--dbpath', str(data), '--replSet', 'rs0', '--bind_ip', '127.0.0.1', '--port', '27017', '--wiredTigerCacheSizeGB', '0.25', '--logpath', str(PRIVATE / 'mongo.log'), '--logappend'])
    with MongoClient('mongodb://127.0.0.1:27017/?replicaSet=rs0', serverSelectionTimeoutMS=15000) as client:
        assert client.admin.command('hello')['isWritablePrimary']
        actual = Path(client.admin.command('getCmdLineOpts')['parsed']['storage']['dbPath']).resolve()
        assert actual == data, 'Different Mongo storage: do not change it'
        assert len(client.ecommerce_defense.list_collection_names()) == 7
    if listening(5000) or listening(5173):
        raise RuntimeError('Demo ports already in use. Inspect existing listeners; never kill unrelated processes.')
    env = dict(os.environ)
    env.update(cfg['environment'])
    assert env['MONGODB_DB'] == 'ecommerce_defense' and env['VNPAY_ENABLED'] == 'false'
    spawn('backend', [cfg['python'], '-X', 'utf8', 'backend/run.py'], env=env)
    front_env = dict(env, VITE_API_BASE_URL='/api/v1')
    spawn('frontend', [cfg['node'], str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5173', '--strictPort'], env=front_env, cwd=ROOT / 'frontend')
    for url in ('http://127.0.0.1:5000/api/v1/health', 'http://127.0.0.1:5173/'):
        for attempt in range(40):
            try:
                with urlopen(url, timeout=2) as response:
                    assert response.status == 200
                break
            except Exception:
                if attempt == 39:
                    raise RuntimeError('Startup failed: inspect private logs') from None
                time.sleep(0.5)
    print(json.dumps({'status': 'LOCAL_DEMO_RUNNING', 'frontend': 'http://127.0.0.1:5173/', 'health': 'http://127.0.0.1:5000/api/v1/health', 'database': 'ecommerce_defense', 'vnpayEnabled': False, 'startedPids': pids}, indent=2))


if __name__ == '__main__':
    start()
