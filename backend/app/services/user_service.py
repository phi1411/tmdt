"""Owner profile/address invariants and minimal admin account management."""
from datetime import datetime, timezone
from bson import ObjectId
from app.errors import AuthenticationError, AuthorizationError, BusinessRuleError, ConflictError, NotFoundError
from app.repositories.user_repository import UserRepository
from app.schemas.user_response import public_account, public_profile, public_address
from app.schemas.user_schema import MAX_VERSION


class UserService:
    def __init__(self, repository=None):
        self.repository = repository if repository is not None else UserRepository()

    def current(self, identity):
        user = self.repository.find_profile(identity['_id'])
        if user is None or user['status'] != 'ACTIVE' or user['tokenVersion'] != identity['tokenVersion']:
            raise AuthenticationError()
        if user['role'] != identity['role']:
            raise AuthorizationError()
        return user

    def profile(self, identity):
        return public_profile(self.current(identity))

    def mutate(self, snapshot, fields, expected_version, revoke=False, no_op=False):
        if snapshot['version'] != expected_version:
            raise ConflictError()
        if not no_op and (snapshot['version'] >= MAX_VERSION or (revoke and snapshot['tokenVersion'] >= MAX_VERSION)):
            raise BusinessRuleError()
        updated = self.repository.compare_and_set(snapshot, fields, datetime.now(timezone.utc), revoke, no_op=no_op)
        if updated is None:
            raise ConflictError()
        return updated

    def update_profile(self, identity, fields, expected_version):
        return public_profile(self.mutate(self.current(identity), fields, expected_version))

    @staticmethod
    def address(user, address_id):
        for address in user['addresses']:
            if address['_id'] == address_id:
                return address
        raise NotFoundError()

    def add_address(self, identity, fields, expected_version):
        user = self.current(identity)
        if user['version'] != expected_version:
            raise ConflictError()
        if len(user['addresses']) >= 10:
            raise BusinessRuleError()
        address = {'_id': ObjectId(), **fields}
        updated = self.mutate(user, {'addresses': [*user['addresses'], address]}, expected_version)
        return {'address': public_address(address), 'version': updated['version']}

    def update_address(self, identity, address_id, fields, expected_version):
        user = self.current(identity)
        address = {**self.address(user, address_id), **fields}
        addresses = [address if a['_id'] == address_id else a for a in user['addresses']]
        updated = self.mutate(user, {'addresses': addresses}, expected_version)
        return {'address': public_address(address), 'version': updated['version']}

    def remove_address(self, identity, address_id, expected_version):
        user = self.current(identity)
        self.address(user, address_id)
        fields = {'addresses': [a for a in user['addresses'] if a['_id'] != address_id]}
        if user['defaultAddressId'] == address_id:
            fields['defaultAddressId'] = None
        self.mutate(user, fields, expected_version)

    def default_address(self, identity, address_id, expected_version):
        user = self.current(identity)
        self.address(user, address_id)
        updated = self.mutate(user, {'defaultAddressId': address_id}, expected_version)
        return {'defaultAddressId': updated['defaultAddressId'], 'version': updated['version']}

    def list_accounts(self, filters, pagination):
        users, total = self.repository.list_accounts(filters, pagination)
        return [public_account(user) for user in users], total

    def account(self, user_id):
        user = self.repository.find_account(user_id)
        if user is None:
            raise NotFoundError()
        return public_account(user)

    def change_status(self, user_id, status, expected_version):
        user = self.repository.find_profile(user_id)
        if user is None:
            raise NotFoundError()
        if user['role'] != 'CUSTOMER':
            raise BusinessRuleError()
        updated = self.mutate(user, {'status': status}, expected_version,
                              revoke=True, no_op=user['status'] == status)
        return public_account(updated)
