"""Owner filters at every customer query; no live product lookup for history."""
from pymongo import ReturnDocument
from app.db import get_db
from app.schemas.order_schema import SUMMARY_FIELDS
from app.errors import ConflictError


class OrderRepository:
    def __init__(self):
        self.collection = get_db().orders

    def find(self, user_id, order_id, session=None):
        return self.collection.find_one({'_id': order_id, 'userId': user_id}, session=session)

    def replay(self, user_id, key, session=None):
        return self.collection.find_one({'userId': user_id, 'checkoutKey': key}, session=session)

    def insert(self, order, session):
        self.collection.insert_one(order, session=session)

    def find_payment(self, order_id, session=None):
        return self.collection.find_one({'_id': order_id}, session=session)

    def due_ids(self, now, limit=100):
        return [o['_id'] for o in self.collection.find({'paymentMethod': 'VNPAY', 'orderStatus': 'PENDING',
            'paymentStatus': {'$in': ['PENDING', 'FAILED']}, 'paymentExpiresAt': {'$lte': now}}, {'_id': 1})
            .sort([('paymentExpiresAt', 1), ('_id', 1)]).limit(limit)]

    def patch_payment(self, order, fields, now, session):
        if order['version'] >= 2147483647:
            raise ConflictError(code='VERSION_LIMIT')
        changed = self.collection.find_one_and_update({'_id': order['_id'], 'version': order['version'],
            'orderStatus': order['orderStatus'], 'paymentStatus': order['paymentStatus']},
            {'$set': {**fields, 'updatedAt': now}, '$inc': {'version': 1}}, return_document=ReturnDocument.AFTER, session=session)
        if changed is None:
            raise ConflictError(code='ORDER_CHANGED')
        return changed

    def list(self, user_id, filters, pagination):
        # One facet read for matching items/count, bounded owner index pattern.
        result = next(self.collection.aggregate([
            {'$match': {**filters, 'userId': user_id}}, {'$sort': {'createdAt': -1, '_id': -1}},
            {'$facet': {'items': [{'$skip': pagination.skip}, {'$limit': pagination.page_size},
                                {'$project': {key: 1 for key in SUMMARY_FIELDS}}],
                        'count': [{'$count': 'total'}]}}
        ]))
        return result['items'], result['count'][0]['total'] if result['count'] else 0

    def cancel(self, order, payment_status, now, session):
        return self.collection.find_one_and_update(
            {'_id': order['_id'], 'userId': order['userId'], 'version': order['version'],
             'orderStatus': {'$in': ['PENDING', 'CONFIRMED']},
             'paymentStatus': {'$nin': ['PAID', 'REVIEW_REQUIRED']}, 'paymentReviewRequired': False,
             'stockReleasedAt': {'$exists': False}, '$and': [{'version': {'$lt': 2147483647}}]},
            {'$set': {'orderStatus': 'CANCELLED', 'cancelledAt': now, 'stockReleasedAt': now,
                      'updatedAt': now, 'paymentStatus': payment_status},
             '$inc': {'version': 1}}, return_document=ReturnDocument.AFTER, session=session)

    def find_admin(self, order_id, session=None):
        return self.collection.find_one({'_id': order_id}, session=session)

    def list_admin(self, filters, pagination):
        result = next(self.collection.aggregate([
            {'$match': filters}, {'$sort': {'createdAt': -1, '_id': -1}},
            {'$facet': {'items': [{'$skip': pagination.skip}, {'$limit': pagination.page_size},
                                {'$project': {key: 1 for key in SUMMARY_FIELDS}}],
                        'count': [{'$count': 'total'}]}}
        ], maxTimeMS=10000, allowDiskUse=False))
        return result['items'], result['count'][0]['total'] if result['count'] else 0

    def transition_admin(self, order, fields, now, session):
        return self.collection.find_one_and_update(
            {'_id': order['_id'], 'version': order['version'],
             'orderStatus': order['orderStatus'], 'paymentStatus': order['paymentStatus'],
             'paymentMethod': order['paymentMethod'], 'paymentReviewRequired': order['paymentReviewRequired'],
             'stockReleasedAt': {'$exists': False}, '$and': [{'version': {'$lt': 2147483647}}]},
            {'$set': {**fields, 'updatedAt': now}, '$inc': {'version': 1}},
            return_document=ReturnDocument.AFTER, session=session)
