"""Access JWT primitives only. Login service must verify credentials first."""
from datetime import datetime, timezone
from uuid import uuid4
import jwt
from flask import current_app
from bson import ObjectId
from app.errors import AuthenticationError
from app.utils.ids import parse_object_id

REQUIRED_CLAIMS = ['sub', 'iat', 'nbf', 'exp', 'iss', 'aud', 'jti', 'tokenVersion']


def create_access_token(user):
    if not isinstance(user.get('_id'), ObjectId) or user.get('status') != 'ACTIVE' or user.get('role') not in {'CUSTOMER', 'ADMIN'} or type(user.get('tokenVersion')) is not int or user['tokenVersion'] < 0:
        raise AuthenticationError()
    config = current_app.config
    now = int(datetime.now(timezone.utc).timestamp())
    claims = {
        'sub': str(user['_id']), 'tokenVersion': user['tokenVersion'],
        'iss': config['JWT_ISSUER'], 'aud': config['JWT_AUDIENCE'],
        'iat': now, 'nbf': now, 'exp': now + config['JWT_ACCESS_TTL_SECONDS'], 'jti': uuid4().hex,
    }
    return jwt.encode(claims, config['JWT_SECRET'], algorithm=config['JWT_ALGORITHM'])


def decode_access_token(token):
    config = current_app.config
    try:
        claims = jwt.decode(
            token, config['JWT_SECRET'], algorithms=[config['JWT_ALGORITHM']],
            issuer=config['JWT_ISSUER'], audience=config['JWT_AUDIENCE'],
            options={'require': REQUIRED_CLAIMS, 'strict_aud': True},
        )
        if any(type(claims[key]) is not int for key in ('iat', 'nbf', 'exp', 'tokenVersion')) or claims['tokenVersion'] < 0:
            raise ValueError('Invalid numeric claims')
        if claims['exp'] <= claims['iat'] or claims['exp'] - claims['iat'] > config['JWT_ACCESS_TTL_SECONDS']:
            raise ValueError('Invalid lifetime')
        if not isinstance(claims['jti'], str) or not 1 <= len(claims['jti']) <= 128:
            raise ValueError('Invalid token identifier')
        parse_object_id(claims['sub'], 'sub')
        return claims
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise AuthenticationError() from None
    except Exception as error:
        # ID parsing produces a public 400 elsewhere; JWT subject failures are 401.
        from app.errors import BadRequestError
        if isinstance(error, BadRequestError):
            raise AuthenticationError() from None
        raise
