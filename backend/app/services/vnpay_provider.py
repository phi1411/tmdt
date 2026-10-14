"""VNPAY 2.1.0 Sandbox adapter: no network I/O, no secrets in metadata."""
import hashlib
import hmac
import ipaddress
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, quote_plus, urlsplit
from flask import current_app
from bson.int64 import Int64
from app.errors import ServiceUnavailableError

VN_TIMEZONE = timezone(timedelta(hours=7))
CALLBACK_REQUIRED = {'vnp_TmnCode', 'vnp_Amount', 'vnp_BankCode', 'vnp_OrderInfo',
                     'vnp_TransactionNo', 'vnp_ResponseCode', 'vnp_TransactionStatus', 'vnp_TxnRef', 'vnp_SecureHash'}
CALLBACK_ALLOWED = CALLBACK_REQUIRED | {'vnp_PayDate', 'vnp_BankTranNo', 'vnp_CardType', 'vnp_SecureHashType'}


class ProviderValidationError(Exception):
    def __init__(self, code='99'):
        self.code = code
        super().__init__('Invalid provider response')


def validate_settings(values, enabled, configuration_error):
    """Validate secrets without including their values in diagnostics."""
    keys = ('VNP_TMN_CODE', 'VNP_HASH_SECRET', 'VNP_PAYMENT_URL', 'VNP_RETURN_URL', 'VNP_IPN_URL')
    result = {key: values.get(key, '') for key in keys}
    complete = all(isinstance(v, str) and v and not v.startswith('REPLACE_') for v in result.values())
    if not complete:
        if enabled:
            raise configuration_error('VNPAY requires all VNP_* credentials and URLs')
        return {key: '' for key in keys}
    if not re.fullmatch(r'[A-Za-z0-9]{8}', result['VNP_TMN_CODE']):
        raise configuration_error('VNP_TMN_CODE must contain 8 alphanumeric characters')
    if result['VNP_HASH_SECRET'] != result['VNP_HASH_SECRET'].strip():
        raise configuration_error('VNP_HASH_SECRET must not have outer whitespace')
    for key in ('VNP_PAYMENT_URL', 'VNP_RETURN_URL', 'VNP_IPN_URL'):
        url = result[key]
        try:
            parsed = urlsplit(url)
            parsed.port
            valid = parsed.hostname and not parsed.username and not parsed.password and not parsed.fragment
            valid = valid and not re.search(r'[\s\\\x00-\x1f\x7f]', url)
            valid = valid and (parsed.scheme == 'https' or (parsed.scheme == 'http' and parsed.hostname in {'localhost', '127.0.0.1', '::1'}))
            if key == 'VNP_PAYMENT_URL':
                valid = valid and parsed.scheme == 'https' and parsed.hostname == 'sandbox.vnpayment.vn' and parsed.path == '/paymentv2/vpcpay.html' and not parsed.query and parsed.port in {None, 443}
            elif key == 'VNP_RETURN_URL':
                valid = valid and 10 <= len(url) <= 255
            else:
                valid = valid and len(url) <= 2048 and not parsed.query
        except ValueError:
            valid = False
        if not valid:
            raise configuration_error(f'{key} is not a valid Sandbox/return/IPN URL')
    return result


def canonical_parameters(values):
    return urlencode(sorted((k, str(v)) for k, v in values.items() if k not in {'vnp_SecureHash', 'vnp_SecureHashType'}),
                     quote_via=quote_plus, encoding='utf-8')


def sign_parameters(values, secret):
    return hmac.new(secret.encode('utf-8'), canonical_parameters(values).encode('utf-8'), hashlib.sha512).hexdigest()


def provider_time(value):
    return value.astimezone(VN_TIMEZONE).strftime('%Y%m%d%H%M%S')


class VnpayProvider:
    def __init__(self):
        self.config = current_app.config

    def require_config(self, creation=False):
        if not self.config.get('VNP_HASH_SECRET') or (creation and not self.config['VNPAY_ENABLED']):
            raise ServiceUnavailableError(code='PAYMENT_UNAVAILABLE', message='VNPAY Sandbox chưa được cấu hình hoặc chưa bật')

    def payment_request(self, order, txn_ref, client_ip, now):
        self.require_config(creation=True)
        address = ipaddress.ip_address(client_ip or '127.0.0.1')
        client_ip = address.exploded if address.version == 6 else str(address)
        return {'version': '2.1.0', 'command': 'pay', 'tmnCode': self.config['VNP_TMN_CODE'],
                'amountScaled': Int64(int(order['total']) * 100), 'currency': 'VND', 'txnRef': txn_ref,
                'orderInfo': 'Thanh toan don hang ' + str(order['_id']).upper(), 'orderType': 'other',
                'locale': 'vn', 'returnUrl': self.config['VNP_RETURN_URL'], 'clientIp': client_ip,
                'createdAt': now, 'expiresAt': order['paymentExpiresAt']}

    def payment_url(self, attempt):
        self.require_config()
        metadata = attempt['paymentRequest']
        if metadata['tmnCode'] != self.config['VNP_TMN_CODE']:
            raise ServiceUnavailableError(code='PAYMENT_UNAVAILABLE')
        mapping = {'version': 'vnp_Version', 'command': 'vnp_Command', 'tmnCode': 'vnp_TmnCode',
                   'amountScaled': 'vnp_Amount', 'currency': 'vnp_CurrCode', 'txnRef': 'vnp_TxnRef',
                   'orderInfo': 'vnp_OrderInfo', 'orderType': 'vnp_OrderType', 'locale': 'vnp_Locale',
                   'returnUrl': 'vnp_ReturnUrl', 'clientIp': 'vnp_IpAddr'}
        params = {target: str(metadata[source]) for source, target in mapping.items()}
        params.update(vnp_CreateDate=provider_time(metadata['createdAt']), vnp_ExpireDate=provider_time(metadata['expiresAt']))
        return self.config['VNP_PAYMENT_URL'] + '?' + canonical_parameters(params) + '&vnp_SecureHash=' + sign_parameters(params, self.config['VNP_HASH_SECRET'])

    def verify(self, args):
        self.require_config()
        if set(args) - CALLBACK_ALLOWED or not CALLBACK_REQUIRED <= set(args) or any(len(args.getlist(k)) != 1 for k in args):
            raise ProviderValidationError('97')
        values = args.to_dict(flat=True)
        if any(not isinstance(v, str) or len(v) > 2048 for v in values.values()):
            raise ProviderValidationError('97')
        signature = values['vnp_SecureHash']
        if not re.fullmatch(r'[a-fA-F0-9]{128}', signature):
            raise ProviderValidationError('97')
        if not hmac.compare_digest(signature.lower(), sign_parameters(values, self.config['VNP_HASH_SECRET'])) or values['vnp_TmnCode'] != self.config['VNP_TMN_CODE']:
            raise ProviderValidationError('97')
        for key, pattern in [('vnp_Amount', r'[0-9]{1,12}'), ('vnp_TxnRef', r'[A-Za-z0-9]{1,100}'),
                             ('vnp_TransactionNo', r'[0-9]{1,15}'), ('vnp_ResponseCode', r'[0-9]{2}'),
                             ('vnp_TransactionStatus', r'[0-9]{2}'), ('vnp_BankCode', r'[A-Za-z0-9]{3,20}')]:
            if not re.fullmatch(pattern, values[key]):
                raise ProviderValidationError()
        if not 1 <= len(values['vnp_OrderInfo']) <= 255 or any(ord(c) < 32 for c in values['vnp_OrderInfo']):
            raise ProviderValidationError()
        for key, pattern in [('vnp_BankTranNo', r'[A-Za-z0-9]{1,255}'), ('vnp_CardType', r'[A-Za-z]{2,20}')]:
            if key in values and not re.fullmatch(pattern, values[key]):
                raise ProviderValidationError()
        successful = values['vnp_ResponseCode'] == values['vnp_TransactionStatus'] == '00'
        transaction_no = str(int(values['vnp_TransactionNo']))
        if successful and transaction_no == '0':
            raise ProviderValidationError()
        paid_at = None
        if 'vnp_PayDate' in values:
            try:
                text = values['vnp_PayDate']
                if not re.fullmatch(r'[0-9]{14}', text):
                    raise ValueError()
                paid_at = datetime.strptime(text, '%Y%m%d%H%M%S').replace(tzinfo=VN_TIMEZONE).astimezone(timezone.utc)
                if provider_time(paid_at) != text:
                    raise ValueError()
            except ValueError:
                raise ProviderValidationError() from None
        return {'txnRef': values['vnp_TxnRef'], 'amountScaled': int(values['vnp_Amount']),
                'success': successful, 'responseCode': values['vnp_ResponseCode'],
                'transactionStatus': values['vnp_TransactionStatus'], 'bankCode': values['vnp_BankCode'],
                'providerTransactionNo': transaction_no if transaction_no != '0' else None,
                'providerPaidAt': paid_at, 'callbackFingerprint': hashlib.sha256(canonical_parameters(values).encode()).hexdigest()}
