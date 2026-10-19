from app.db import get_db


class ReviewRepository:
    def __init__(self):
        self.collection = get_db().reviews

    def list_by_product(self, product_id, limit=20, status='VISIBLE'):
        return list(self.collection.find({'productId': product_id, 'status': status}).sort('createdAt', -1).limit(limit))

    def find_user_review(self, user_id, order_id, product_id, session=None):
        return self.collection.find_one({
            'userId': user_id,
            'orderId': order_id,
            'productId': product_id,
        }, session=session)

    def insert(self, document, session=None):
        return self.collection.insert_one(document, session=session).inserted_id

    def rating_summary(self, product_id, session=None):
        rows = list(self.collection.aggregate([
            {'$match': {'productId': product_id, 'status': 'VISIBLE'}},
            {'$group': {'_id': '$rating', 'count': {'$sum': 1}}},
        ], session=session, maxTimeMS=10000))
        counts = {str(i): 0 for i in range(1, 6)}
        counts.update({str(row['_id']): row['count'] for row in rows})
        total = sum(counts.values())
        return {'totalReviews': total, 'averageRating': round(sum(int(k)*v for k, v in counts.items())/total, 1) if total else 0.0,
                'starsBreakdown': counts}

    def feed(self, product_id, pagination, rating=None, has_comment=False):
        query = {'productId': product_id, 'status': 'VISIBLE'}
        if rating is not None:
            query['rating'] = rating
        if has_comment:
            query['reviewText'] = {'$regex': r'\S'}
        result = next(self.collection.aggregate([
            {'$match': query}, {'$sort': {'createdAt': -1, '_id': -1}},
            {'$facet': {'items': [{'$skip': pagination.skip}, {'$limit': pagination.page_size},
                {'$project': {'orderId': 0, 'orderCode': 0, 'userId': 0, 'schemaVersion': 0}}],
                'count': [{'$count': 'total'}]}}
        ], maxTimeMS=10000))
        return result['items'], result['count'][0]['total'] if result['count'] else 0
