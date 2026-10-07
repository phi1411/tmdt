"""Auth allowlists and email normalization; passwords are never trimmed."""
import re
from app.errors import ValidationError
from app.schemas.user_schema import NAME, PHONE, object_schema, normalize_fields

EMAIL = {'type': 'string', 'minLength': 1, 'maxLength': 254}
PASSWORD = {'type': 'string', 'minLength': 12, 'maxLength': 128}
REGISTER_SCHEMA = object_schema({'name': NAME, 'email': EMAIL, 'password': PASSWORD, 'phone': PHONE},
                                ['name', 'email', 'password'])
LOGIN_SCHEMA = object_schema({'email': EMAIL, 'password': PASSWORD}, ['email', 'password'])
PASSWORD_SCHEMA = object_schema({'currentPassword': PASSWORD, 'newPassword': PASSWORD},
                                ['currentPassword', 'newPassword'])


def normalize_email(email):
    normalized = email.strip().lower()
    if len(normalized) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', normalized):
        raise ValidationError(details=[{'field': 'email', 'reason': 'Email không hợp lệ'}])
    return normalized


def register_input(payload):
    return {**normalize_fields(payload, {'name', 'phone'}), 'email': normalize_email(payload['email']),
            'password': payload['password']}
