"""Map framework/driver/unexpected exceptions to one safe API envelope."""
from flask import g, jsonify, request
from pymongo.errors import DuplicateKeyError, PyMongoError
from werkzeug.exceptions import HTTPException
from app.errors import APIError, ConflictError, ServiceUnavailableError
from app.utils.logging import log_failure
from app.utils.responses import request_meta


def register_error_handlers(app):
    def render(error):
        response = jsonify({'error': {'code': error.code, 'message': error.message, 'details': error.details}, 'meta': request_meta()})
        response.status_code = error.status_code
        if error.status_code == 401:
            response.headers['WWW-Authenticate'] = 'Bearer'
        return response

    app.register_error_handler(APIError, render)

    @app.errorhandler(DuplicateKeyError)
    def duplicate(error):
        return render(ConflictError(code='DUPLICATE_RESOURCE'))

    @app.errorhandler(PyMongoError)
    def database(error):
        log_failure(app, 'database.failure', error, getattr(g, 'request_id', None), request.method, request.endpoint)
        return render(ServiceUnavailableError())

    @app.errorhandler(HTTPException)
    def http(error):
        codes = {400: 'BAD_REQUEST', 401: 'UNAUTHENTICATED', 403: 'FORBIDDEN', 404: 'NOT_FOUND', 405: 'METHOD_NOT_ALLOWED', 409: 'CONFLICT', 413: 'PAYLOAD_TOO_LARGE', 415: 'UNSUPPORTED_MEDIA_TYPE', 422: 'VALIDATION_ERROR', 429: 'RATE_LIMITED', 500: 'INTERNAL_ERROR', 503: 'SERVICE_UNAVAILABLE'}
        messages = {400: 'Yêu cầu không hợp lệ', 401: 'Phiên đăng nhập không hợp lệ', 403: 'Bạn không có quyền thực hiện thao tác này', 404: 'Không tìm thấy tài nguyên', 405: 'Phương thức không được hỗ trợ', 409: 'Dữ liệu đã thay đổi hoặc bị trùng', 413: 'Nội dung yêu cầu vượt giới hạn', 415: 'Yêu cầu phải dùng JSON', 422: 'Dữ liệu không hợp lệ', 429: 'Quá nhiều yêu cầu', 500: 'Đã xảy ra lỗi máy chủ', 503: 'Dịch vụ dữ liệu tạm thời không sẵn sàng'}
        if error.code >= 500:
            log_failure(app, 'server.http_failure', error, getattr(g, 'request_id', None), request.method, request.endpoint)
        safe = APIError(code=codes.get(error.code, 'HTTP_ERROR'), message=messages.get(error.code, 'Yêu cầu không thể được xử lý'))
        safe.status_code = error.code
        response = render(safe)
        # Keep HTTP semantics such as Allow without copying HTML/error descriptions.
        for key, value in error.get_headers():
            if key.lower() in {'allow', 'retry-after'}:
                response.headers[key] = value
        return response

    @app.errorhandler(Exception)
    def unexpected(error):
        log_failure(app, 'server.failure', error, getattr(g, 'request_id', None), request.method, request.endpoint)
        return render(APIError())
