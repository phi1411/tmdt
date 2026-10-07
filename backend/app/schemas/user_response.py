"""Explicit public DTOs; never expose a MongoDB entity as a response."""
ACCOUNT_FIELDS = ('_id', 'name', 'email', 'phone', 'role', 'status', 'version', 'createdAt')
ADDRESS_FIELDS = ('_id', 'receiverName', 'phone', 'addressLine', 'province', 'ward', 'district', 'label')


def public_account(user):
    return {key: user[key] for key in ACCOUNT_FIELDS if key in user}


def public_address(address):
    return {key: address[key] for key in ADDRESS_FIELDS if key in address}


def public_profile(user):
    return {**public_account(user), 'addresses': [public_address(a) for a in user['addresses']],
            'defaultAddressId': user['defaultAddressId'], 'updatedAt': user['updatedAt']}
