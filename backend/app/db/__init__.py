"""One process-local MongoClient per app; app lifetime, not request lifetime."""
import atexit
from flask import current_app
from pymongo import MongoClient, ReadPreference
from pymongo.errors import PyMongoError
from pymongo.write_concern import WriteConcern
from app.config import ConfigurationError
from app.utils.logging import log_failure


class MongoConnection:
    def __init__(self, client, database, replica):
        self.client = client
        self.database = database
        self.replica = replica
        self.closed = False

    def health(self):
        self.client.admin.command('ping')
        hello = self.client.admin.command('hello')
        if hello.get('setName') != self.replica or not hello.get('isWritablePrimary') or not hello.get('logicalSessionTimeoutMinutes'):
            raise ConfigurationError('MongoDB replica set must have a writable primary and sessions')
        return {'backend': 'ok', 'database': 'ok', 'replicaSet': 'ok'}

    def close(self):
        if not self.closed:
            self.client.close()
            self.closed = True
            atexit.unregister(self.close)


def init_mongo(app):
    timeout = app.config['MONGODB_TIMEOUT_MS']
    client = MongoClient(
        app.config['MONGODB_URI'], replicaSet=app.config['MONGODB_REPLICA_SET'],
        serverSelectionTimeoutMS=timeout, connectTimeoutMS=timeout, socketTimeoutMS=timeout,
        tz_aware=True, connect=False, appname='tmdt-backend',
    )
    connection = MongoConnection(client, client.get_database(
        app.config['MONGODB_DB'], read_preference=ReadPreference.PRIMARY,
        write_concern=WriteConcern('majority'),
    ), app.config['MONGODB_REPLICA_SET'])
    try:
        connection.health()
    except (PyMongoError, ConfigurationError) as error:
        log_failure(app, 'database.startup_failed', error)
        connection.close()
        raise ConfigurationError('MongoDB connection/topology is not ready') from None
    app.extensions['mongo'] = connection
    atexit.register(connection.close)


def get_mongo():
    return current_app.extensions['mongo']


def get_db():
    return get_mongo().database
