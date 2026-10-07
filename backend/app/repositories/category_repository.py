from pymongo import ReturnDocument
from app.db import get_db

CATEGORY_PROJECTION = {key: 1 for key in ('_id', 'name', 'slug', 'productType', 'description', 'status', 'version', 'createdAt', 'updatedAt')}


class CategoryRepository:
    def __init__(self):
        self.collection = get_db().categories

    def find(self, query, session=None):
        return self.collection.find_one(query, CATEGORY_PROJECTION, session=session)

    def list(self, query, pagination):
        result = next(self.collection.aggregate([
            {'$match': query}, {'$sort': {'_id': 1}},
            {'$facet': {'items': [{'$skip': pagination.skip}, {'$limit': pagination.page_size}, {'$project': CATEGORY_PROJECTION}],
                        'count': [{'$count': 'total'}]}}
        ]))
        return result['items'], result['count'][0]['total'] if result['count'] else 0

    def insert(self, document, session=None):
        self.collection.insert_one(document, session=session)

    def patch(self, query, fields, now, session=None):
        guarded = {'$and': [query, {'version': {'$lt': 2147483647}}]}
        return self.collection.find_one_and_update(guarded, {'$set': {**fields, 'updatedAt': now}, '$inc': {'version': 1}},
            projection=CATEGORY_PROJECTION, return_document=ReturnDocument.AFTER, session=session)

    def guard_active(self, category_id, product_type, now, session):
        return self.patch({'_id': category_id, 'productType': product_type, 'status': 'ACTIVE'}, {}, now, session)

    def delete(self, category_id, session):
        self.collection.delete_one({'_id': category_id}, session=session)
