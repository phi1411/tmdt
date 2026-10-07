from pymongo import ReturnDocument
from app.db import get_db

PRODUCT_PROJECTION = {key: 1 for key in ('_id', 'sku', 'name', 'slug', 'categoryId', 'productType', 'brand',
    'description', 'price', 'stock', 'images', 'attributes', 'status', 'version', 'createdAt', 'updatedAt')}


class ProductRepository:
    def __init__(self):
        self.collection = get_db().products

    def pipeline(self, query, sort=None, public=False):
        stages = [{'$match': query}]
        if sort:
            stages.append({'$sort': dict(sort)})
        stages.append({'$lookup': {'from': 'categories', 'localField': 'categoryId', 'foreignField': '_id',
            'pipeline': ([{'$match': {'status': 'ACTIVE'}}] if public else []) +
                [{'$project': {'_id': 1, 'name': 1, 'slug': 1, 'productType': 1}}], 'as': 'category'}})
        if public:
            stages.append({'$match': {'category.0': {'$exists': True}}})
        stages.append({'$set': {'category': {'$ifNull': [{'$arrayElemAt': ['$category', 0]}, None]}}})
        return stages

    def list(self, query, sort, pagination, public=False):
        projection = {**PRODUCT_PROJECTION, 'category': 1}
        if public:
            projection.pop('status')
        result = next(self.collection.aggregate(self.pipeline(query, sort, public) + [
            {'$facet': {'items': [{'$skip': pagination.skip}, {'$limit': pagination.page_size}, {'$project': projection}],
                        'count': [{'$count': 'total'}]}}
        ]))
        return result['items'], result['count'][0]['total'] if result['count'] else 0

    def detail(self, query, public=False):
        projection = {**PRODUCT_PROJECTION, 'category': 1}
        if public:
            projection.pop('status')
        return next(self.collection.aggregate(self.pipeline(query, public=public) + [{'$project': projection}, {'$limit': 1}]), None)

    def find(self, product_id, session):
        return self.collection.find_one({'_id': product_id}, PRODUCT_PROJECTION, session=session)

    def referenced(self, category_id, session):
        return self.collection.find_one({'categoryId': category_id}, {'_id': 1}, session=session) is not None

    def insert(self, document, session):
        self.collection.insert_one(document, session=session)

    def patch(self, product_id, version, fields, now, session):
        return self.collection.find_one_and_update({'_id': product_id, 'version': version},
            {'$set': {**fields, 'updatedAt': now}, '$inc': {'version': 1}}, projection=PRODUCT_PROJECTION,
            return_document=ReturnDocument.AFTER, session=session)
