"""Shared success/empty/pagination responses under the locked API convention."""
from flask import g, jsonify, make_response


def request_meta(extra=None):
    return {**(extra or {}), 'requestId': g.request_id}


def success(data, status=200, meta=None, location=None):
    if status not in {200, 201}:
        raise ValueError('Success response must be 200 or 201; use no_content for 204')
    response = jsonify({'data': data, 'meta': request_meta(meta)})
    response.status_code = status
    if location:
        response.headers['Location'] = location
    return response


def no_content():
    return make_response('', 204)


def paginated(data, pagination, total):
    return success(data, meta=pagination.metadata(total))
