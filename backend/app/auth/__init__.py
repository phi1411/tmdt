"""Shared Bearer authentication and current database role/version guards."""
from functools import wraps
from flask import g, request
from app.auth.tokens import decode_access_token
from app.errors import AuthenticationError, AuthorizationError
from app.repositories.user_repository import UserRepository
from app.utils.ids import parse_object_id


def get_current_user():
    if hasattr(g, 'current_user'):
        return g.current_user
    parts = request.headers.get('Authorization', '').split()
    if len(parts) != 2 or parts[0].lower() != 'bearer' or len(parts[1]) > 4096:
        raise AuthenticationError()
    claims = decode_access_token(parts[1])
    user = UserRepository().find_auth_identity(parse_object_id(claims['sub']))
    if user is None or user.get('status') != 'ACTIVE' or user.get('role') not in {'CUSTOMER', 'ADMIN'} or type(user.get('tokenVersion')) is not int or user['tokenVersion'] != claims['tokenVersion']:
        raise AuthenticationError()
    g.current_user = user
    return user


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        get_current_user()
        return view(*args, **kwargs)
    return wrapped


def require_roles(*roles):
    if not roles or not set(roles) <= {'CUSTOMER', 'ADMIN'}:
        raise ValueError('Role guard must use CUSTOMER or ADMIN')
    def decorate(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if get_current_user()['role'] not in roles:
                raise AuthorizationError()
            return view(*args, **kwargs)
        return wrapped
    return decorate
