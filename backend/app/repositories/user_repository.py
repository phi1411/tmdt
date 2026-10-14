"""User queries and single-document compare-and-set writes; no business logic."""
import re
from pymongo import ReturnDocument
from app.db import get_db
from app.schemas.user_response import ACCOUNT_FIELDS

ACCOUNT_PROJECTION = {key: 1 for key in ACCOUNT_FIELDS}
PROFILE_PROJECTION = {**ACCOUNT_PROJECTION, 'addresses': 1, 'defaultAddressId': 1, 'updatedAt': 1, 'tokenVersion': 1}
CREDENTIAL_PROJECTION = {**ACCOUNT_PROJECTION, 'tokenVersion': 1, 'passwordHash': 1}


class UserRepository:
    def __init__(self, database=None):
        self.database = database if database is not None else get_db()

    def find_auth_identity(self, user_id):
        return self.database.users.find_one(
            {'_id': user_id}, {'_id': 1, 'role': 1, 'status': 1, 'tokenVersion': 1},
        )

    def find_credentials(self, email):
        return self.database.users.find_one({'email': email}, CREDENTIAL_PROJECTION)

    def find_credentials_by_id(self, user_id):
        return self.database.users.find_one({'_id': user_id}, CREDENTIAL_PROJECTION)

    def find_profile(self, user_id):
        return self.database.users.find_one({'_id': user_id}, PROFILE_PROJECTION)

    def find_checkout_user(self, identity, session=None):
        return self.database.users.find_one(
            {'_id': identity['_id'], 'status': 'ACTIVE', 'role': 'CUSTOMER',
             'tokenVersion': identity['tokenVersion']}, PROFILE_PROJECTION, session=session)

    def find_account(self, user_id):
        return self.database.users.find_one({'_id': user_id}, ACCOUNT_PROJECTION)

    def insert(self, document):
        self.database.users.insert_one(document)
        return document

    def compare_and_set(self, snapshot, fields, now, revoke=False, extra_filter=None, no_op=False):
        predicate = {key: snapshot[key] for key in ('_id', 'version', 'role', 'status', 'tokenVersion')}
        predicate.update(extra_filter or {})
        update = {'$set': fields} if no_op else {
            '$set': {**fields, 'updatedAt': now},
            '$inc': {'version': 1, **({'tokenVersion': 1} if revoke else {})},
        }
        return self.database.users.find_one_and_update(
            predicate, update, projection=PROFILE_PROJECTION, return_document=ReturnDocument.AFTER,
        )

    def change_password(self, identity, password_hash, new_hash, now):
        return self.database.users.find_one_and_update(
            {'_id': identity['_id'], 'role': identity['role'], 'status': 'ACTIVE',
             'tokenVersion': identity['tokenVersion'], 'passwordHash': password_hash,
             'version': {'$lt': 2147483647}},
            {'$set': {'passwordHash': new_hash, 'updatedAt': now}, '$inc': {'version': 1, 'tokenVersion': 1}},
            projection=PROFILE_PROJECTION, return_document=ReturnDocument.AFTER,
        )

    def list_accounts(self, filters, pagination):
        predicate = {key: value for key, value in filters.items() if key in {'role', 'status'}}
        if filters.get('q'):
            literal = re.escape(filters['q'])
            predicate['$or'] = [{field: {'$regex': literal, '$options': 'i'}} for field in ('name', 'email')]
        total = self.database.users.count_documents(predicate)
        accounts = list(self.database.users.find(predicate, ACCOUNT_PROJECTION).sort(
            [('createdAt', -1), ('_id', -1)],
        ).skip(pagination.skip).limit(pagination.page_size))
        return accounts, total
