"""Strict JSON Schema API validation, separate from MongoDB validators."""
from jsonschema import Draft202012Validator
from jsonschema.validators import extend
from flask import request
from app.errors import ValidationError

type_checker = Draft202012Validator.TYPE_CHECKER.redefine('integer', lambda checker, value: type(value) is int)
RequestValidator = extend(Draft202012Validator, type_checker=type_checker)


def validate_payload(payload, schema):
    RequestValidator.check_schema(schema)
    details = []
    for error in RequestValidator(schema).iter_errors(payload):
        path = '.'.join(str(p) for p in error.absolute_path) or '$'
        if error.validator == 'required' and isinstance(error.instance, dict):
            for missing in error.validator_value:
                if missing not in error.instance:
                    details.append({'field': missing if path == '$' else f'{path}.{missing}', 'reason': 'Thiếu trường bắt buộc'})
            if len(details) >= 50:
                details = details[:50]
                break
            continue
        # jsonschema's default message embeds received values; never expose it.
        reason = {
            'type': 'Kiểu dữ liệu không hợp lệ', 'enum': 'Giá trị không được hỗ trợ',
            'required': 'Thiếu trường bắt buộc', 'additionalProperties': 'Có trường không được phép',
            'minimum': 'Giá trị nhỏ hơn giới hạn', 'maximum': 'Giá trị lớn hơn giới hạn',
            'minLength': 'Nội dung quá ngắn', 'maxLength': 'Nội dung quá dài',
            'minItems': 'Không đủ phần tử', 'maxItems': 'Quá nhiều phần tử',
            'pattern': 'Định dạng không hợp lệ',
        }.get(error.validator, 'Giá trị không hợp lệ')
        details.append({'field': path, 'reason': reason})
        if len(details) >= 50:
            break
    if details:
        raise ValidationError(details=details)
    return payload


def parse_json_body(schema):
    # Flask maps unsupported content type to 415 and malformed JSON to 400.
    return validate_payload(request.get_json(), schema)


def single_query_values(args, allowed):
    details = []
    for key in args:
        if key not in allowed:
            details.append({'field': '$query', 'reason': 'Có bộ lọc không được hỗ trợ'})
        elif len(args.getlist(key)) != 1:
            details.append({'field': key, 'reason': 'Tham số không được lặp lại'})
    if details:
        raise ValidationError(details=details[:50])
    return args.to_dict(flat=True)
