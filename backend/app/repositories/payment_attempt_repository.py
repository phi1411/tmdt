"""Payment metadata/idempotency queries; all writes share the service session."""
from app.db import get_db
from app.errors import ConflictError
from pymongo import ReturnDocument


class PaymentAttemptRepository:
    def __init__(self):
        self.collection = get_db().payment_attempts

    def invalidate_pending(self, order_id, now, session):
        if self.collection.find_one({'orderId': order_id, 'status': 'PENDING', 'version': {'$gte': 2147483647}}, {'_id': 1}, session=session):
            raise ConflictError(code='VERSION_LIMIT')
        return self.collection.update_many({'orderId': order_id, 'status': 'PENDING'},
            {'$set': {'status': 'EXPIRED', 'expiredAt': now, 'updatedAt': now}, '$inc': {'version': 1}},
            session=session)

    def insert(self, attempt, session):
        self.collection.insert_one(attempt, session=session)

    def find(self, attempt_id, session=None):
        return self.collection.find_one({'_id': attempt_id}, session=session)

    def by_reference(self, txn_ref, session=None):
        return self.collection.find_one({'provider': 'VNPAY', 'txnRef': txn_ref}, session=session)

    def replay(self, order_id, key, session=None):
        return self.collection.find_one({'orderId': order_id, 'attemptKey': key}, session=session)

    def pending(self, order_id, session=None):
        return self.collection.find_one({'orderId': order_id, 'status': 'PENDING'}, session=session)

    def latest(self, order_id):
        return self.collection.find_one({'orderId': order_id}, sort=[('createdAt', -1), ('_id', -1)])

    def patch(self, attempt, fields, now, session):
        if attempt['version'] >= 2147483647:
            raise ConflictError(code='VERSION_LIMIT')
        result = self.collection.find_one_and_update({'_id': attempt['_id'], 'version': attempt['version'], 'status': attempt['status']},
            {'$set': {**fields, 'updatedAt': now}, '$inc': {'version': 1},
             **({'$unset': {k: '' for k in ('providerPaidAt', 'providerTransactionNo') if k not in fields}}
                if 'callbackFingerprint' in fields and any(k not in fields for k in ('providerPaidAt', 'providerTransactionNo')) else {})},
            return_document=ReturnDocument.AFTER, session=session)
        if result is None:
            raise ConflictError(code='PAYMENT_ATTEMPT_CHANGED')
        return result
