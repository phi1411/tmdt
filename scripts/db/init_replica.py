"""Initialize rs0 once, and refuse to reconfigure an unrelated instance."""
import time
from pymongo import MongoClient
from pymongo.errors import OperationFailure

if __name__ == '__main__':
    with MongoClient('mongodb://localhost:27017/?directConnection=true', serverSelectionTimeoutMS=10000) as client:
        if not client.server_info()['version'].startswith('8.0.'):
            raise RuntimeError('MongoDB Community 8.0 required')
        try:
            config = client.admin.command('replSetGetConfig')['config']
            if config['_id'] != 'rs0' or len(config['members']) != 1 or config['members'][0]['host'] != 'localhost:27017':
                raise RuntimeError('Existing replica configuration differs; refusing reconfiguration')
        except OperationFailure as exc:
            if exc.code != 94:
                raise
            client.admin.command('replSetInitiate', {'_id': 'rs0', 'members': [{'_id': 0, 'host': 'localhost:27017'}]})
        for _ in range(45):
            if client.admin.command('hello').get('isWritablePrimary'):
                print(f"MongoDB {client.server_info()['version']}; rs0 PRIMARY ready")
                break
            time.sleep(1)
        else:
            raise RuntimeError('Replica primary election timed out')
