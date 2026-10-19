from pymongo import ReturnDocument
from app.db import get_db

PRODUCT_PROJECTION = {key: 1 for key in ('_id', 'sku', 'name', 'slug', 'categoryId', 'productType', 'brand',
    'description', 'price', 'stock', 'images', 'attributes', 'status', 'version', 'createdAt', 'updatedAt',
    'tierVariations', 'skus', 'ratingSummary')}


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

    def find_many(self, product_ids, session=None):
        return list(self.collection.find({'_id': {'$in': list(product_ids)}}, PRODUCT_PROJECTION, session=session))

    def decrement_stock(self, product, quantity, now, session, sku_quantities=None):
        predicate = {'_id': product['_id'], 'version': product['version'], 'status': 'ACTIVE',
                     'stock': {'$gte': quantity}, '$and': [{'version': {'$lt': 2147483647}}]}
        fields = {'updatedAt': now}
        if product.get('tierVariations'):
            if not sku_quantities or sum(sku_quantities.values()) != quantity:
                return False
            variants = [dict(sku) for sku in product['skus']]
            by_id = {sku['skuId']: sku for sku in variants}
            for sku_id, count in sku_quantities.items():
                if sku_id not in by_id or by_id[sku_id]['stock'] < count:
                    return False
                by_id[sku_id]['stock'] -= count
                predicate['$and'].append({'skus': {'$elemMatch': {'skuId': sku_id, 'stock': {'$gte': count}}}})
            fields['skus'] = variants
        return self.collection.update_one(predicate,
            {'$inc': {'stock': -quantity, 'version': 1}, '$set': fields}, session=session).matched_count

    def restore_stock(self, product_id, quantity, now, session, sku_quantities=None):
        fields = {'updatedAt': now}
        predicate = {'_id': product_id, 'version': {'$lt': 2147483647}, 'stock': {'$lte': 2147483647 - quantity}}
        if sku_quantities:
            product = self.find(product_id, session)
            if not product or sum(sku_quantities.values()) != quantity:
                return False
            variants = [dict(sku) for sku in product.get('skus', [])]
            by_id = {sku['skuId']: sku for sku in variants}
            for sku_id, count in sku_quantities.items():
                if sku_id not in by_id or by_id[sku_id]['stock'] > 2147483647 - count:
                    return False
                by_id[sku_id]['stock'] += count
            predicate['version'] = product['version']
            fields['skus'] = variants
        return self.collection.update_one(predicate,
            {'$inc': {'stock': quantity, 'version': 1}, '$set': fields}, session=session).matched_count

    def referenced(self, category_id, session):
        return self.collection.find_one({'categoryId': category_id}, {'_id': 1}, session=session) is not None

    def insert(self, document, session):
        self.collection.insert_one(document, session=session)

    def update_rating_summary(self, product_id, rating_summary, session=None, expected_version=None, now=None):
        query = {'_id': product_id, 'version': expected_version}
        return self.collection.update_one(query,
            {'$set': {'ratingSummary': rating_summary, 'updatedAt': now}, '$inc': {'version': 1}}, session=session)

    def patch(self, product_id, version, fields, now, session):
        return self.collection.find_one_and_update({'_id': product_id, 'version': version},
            {'$set': {**fields, 'updatedAt': now}, '$inc': {'version': 1}}, projection=PRODUCT_PROJECTION,
            return_document=ReturnDocument.AFTER, session=session)
