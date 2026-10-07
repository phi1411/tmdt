"""Public API error classes. Details contain field/reason, never raw input."""


class APIError(Exception):
    status_code = 500
    code = 'INTERNAL_ERROR'
    message = 'Đã xảy ra lỗi máy chủ'

    def __init__(self, message=None, details=None, code=None):
        self.message = message or type(self).message
        self.details = details or []
        self.code = code or type(self).code
        super().__init__(self.message)


class BadRequestError(APIError):
    status_code, code, message = 400, 'BAD_REQUEST', 'Yêu cầu không hợp lệ'


class AuthenticationError(APIError):
    status_code, code, message = 401, 'UNAUTHENTICATED', 'Phiên đăng nhập không hợp lệ hoặc đã hết hạn'


class AuthorizationError(APIError):
    status_code, code, message = 403, 'FORBIDDEN', 'Bạn không có quyền thực hiện thao tác này'


class NotFoundError(APIError):
    status_code, code, message = 404, 'NOT_FOUND', 'Không tìm thấy tài nguyên'


class ConflictError(APIError):
    status_code, code, message = 409, 'CONFLICT', 'Dữ liệu đã thay đổi hoặc bị trùng'


class BusinessRuleError(ConflictError):
    code, message = 'BUSINESS_RULE_VIOLATION', 'Thao tác không phù hợp trạng thái hiện tại'


class ValidationError(APIError):
    status_code, code, message = 422, 'VALIDATION_ERROR', 'Dữ liệu không hợp lệ'


class ServiceUnavailableError(APIError):
    status_code, code, message = 503, 'SERVICE_UNAVAILABLE', 'Dịch vụ dữ liệu tạm thời không sẵn sàng'
