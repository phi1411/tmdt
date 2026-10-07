"""Registration, credential verification and password revocation use cases."""
from datetime import datetime, timezone
from bson import ObjectId
from flask import current_app
from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import create_access_token
from app.errors import AuthenticationError, BusinessRuleError
from app.repositories.user_repository import UserRepository
from app.schemas.user_response import public_account
from app.schemas.user_schema import MAX_VERSION


class AuthService:
    def __init__(self, repository=None):
        self.repository = repository if repository is not None else UserRepository()

    def register(self, values):
        now = datetime.now(timezone.utc)
        user = self.repository.insert({
            '_id': ObjectId(), 'schemaVersion': 1, 'createdAt': now, 'updatedAt': now,
            'email': values['email'], 'passwordHash': hash_password(values['password']),
            'role': 'CUSTOMER', 'status': 'ACTIVE', 'tokenVersion': 0, 'version': 1,
            'name': values['name'], 'phone': values.get('phone', ''),
            'addresses': [], 'defaultAddressId': None,
        })
        return {'user': public_account(user)}

    def login(self, email, password):
        user = self.repository.find_credentials(email)
        # Missing and blocked accounts still perform the same password verification.
        stored_hash = user['passwordHash'] if user else current_app.extensions['auth_dummy_hash']
        valid = verify_password(stored_hash, password)
        if not valid or user is None or user['status'] != 'ACTIVE':
            raise AuthenticationError(message='Email hoặc mật khẩu không hợp lệ')
        return {'accessToken': create_access_token(user),
                'expiresIn': current_app.config['JWT_ACCESS_TTL_SECONDS'], 'user': public_account(user)}

    def change_password(self, identity, current_password, new_password):
        # Credentials are read privately; none of them leave the service.
        user = self.repository.find_credentials_by_id(identity['_id'])
        if user is None or user['tokenVersion'] != identity['tokenVersion'] or not verify_password(user['passwordHash'], current_password):
            raise AuthenticationError(message='Mật khẩu hiện tại hoặc phiên đăng nhập không hợp lệ')
        if user['tokenVersion'] >= MAX_VERSION:
            raise BusinessRuleError()
        result = self.repository.change_password(identity, user['passwordHash'], hash_password(new_password),
                                                 datetime.now(timezone.utc))
        if result is None:
            raise AuthenticationError()
        return {'reauthenticationRequired': True}
