"""One cart per owner; all mutations use the existing version CAS."""
from bson import ObjectId
from pymongo import ReturnDocument
from app.db import get_db


class CartRepository:
    def __init__(self):
        self.collection = get_db().carts

    def find(self, user_id, session=None):
        return self.collection.find_one({'userId': user_id}, session=session)

    def create(self, user_id, items, now):
        cart = {'_id': ObjectId(), 'schemaVersion': 1, 'userId': user_id, 'version': 1,
                'items': items, 'createdAt': now, 'updatedAt': now}
        self.collection.insert_one(cart)
        return cart

    def replace_items(self, user_id, version, items, now, session=None):
        return self.collection.find_one_and_update(
            {'userId': user_id, 'version': version, '$and': [{'version': {'$lt': 2147483647}}]},
            {'$set': {'items': items, 'updatedAt': now}, '$inc': {'version': 1}},
            return_document=ReturnDocument.AFTER, session=session)
