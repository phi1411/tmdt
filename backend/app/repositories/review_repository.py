from app.db import get_db


class ReviewRepository:
    def __init__(self):
        self.collection = get_db().reviews

    def list_by_product(self, product_id, limit=20, status='VISIBLE'):
        return list(self.collection.find({'productId': product_id, 'status': status}).sort('createdAt', -1).limit(limit))

    def insert(self, document, session=None):
        return self.collection.insert_one(document, session=session).inserted_id
