from datetime import datetime, timezone
from urllib.parse import urlsplit
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from app.errors import ConflictError, NotFoundError, ValidationError
from app.repositories.review_repository import ReviewRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.review_schema import review_response
from app.schemas.pagination import Pagination
from app.services.catalog_transaction import catalog_transaction
from app.utils.ids import parse_object_id


class ReviewService:
    def __init__(self):
        self.reviews = ReviewRepository()
        self.products = ProductRepository()
        self.orders = OrderRepository()

    def public_product(self, identifier, session=None):
        query = {'_id': ObjectId(identifier)} if ObjectId.is_valid(identifier) else {'slug': identifier}
        product = self.products.collection.find_one({**query, 'status': 'ACTIVE'}, session=session)
        category = CategoryRepository().find({'_id': product['categoryId']}, session) if product else None
        if not product or not category or category['status'] != 'ACTIVE' or category['productType'] != product['productType']:
            raise NotFoundError(message='Không tìm thấy sản phẩm')
        return product

    def get_product_reviews(self, identifier, pagination=None, rating=None, has_comment=False):
        product = self.public_product(str(identifier))
        pagination = pagination or Pagination()
        items, total = self.reviews.feed(product['_id'], pagination, rating, has_comment)
        return [review_response(item) for item in items], self.reviews.rating_summary(product['_id']), pagination.metadata(total)

    def create_review(self, user, identifier, data):
        for url in data.get('images', []):
            try:
                parsed = urlsplit(url)
                valid = parsed.hostname and not parsed.username and not parsed.password and not any(c.isspace() or ord(c) < 32 or c == '\\' for c in url)
                valid = valid and (parsed.scheme == 'https' or (parsed.scheme == 'http' and parsed.hostname in {'localhost', '127.0.0.1'}))
                parsed.port
            except ValueError:
                valid = False
            if not valid:
                raise ValidationError(details=[{'field': 'images', 'reason': 'Ảnh phải là URL HTTPS hợp lệ'}])
        order_id = parse_object_id(data['orderId'].lower(), 'orderId')
        now, review_id = datetime.now(timezone.utc), ObjectId()

        def write(session):
            product = self.public_product(identifier, session)
            order = self.orders.find(user['_id'], order_id, session)
            if not order:
                raise NotFoundError(message='Không tìm thấy đơn hàng')
            if order.get('orderStatus') != 'COMPLETED' or order.get('paymentStatus') != 'PAID':
                raise ConflictError(code='ORDER_NOT_COMPLETED', message='Chỉ đánh giá đơn đã hoàn tất và thanh toán')
            item = next((item for item in order['items'] if item['productId'] == product['_id']), None)
            if not item:
                raise ConflictError(code='PRODUCT_NOT_IN_ORDER')
            if self.reviews.find_user_review(user['_id'], order_id, product['_id'], session):
                raise ConflictError(code='ALREADY_REVIEWED')
            if product['version'] >= 2147483647:
                raise ConflictError(code='VERSION_LIMIT')
            name = user.get('name') or order['customerSnapshot']['name']
            document = {'_id': review_id, 'schemaVersion': 1, 'createdAt': now, 'updatedAt': now,
                'productId': product['_id'], 'orderId': order_id, 'orderCode': order['orderCode'], 'userId': user['_id'],
                'userSnapshot': {'displayName': name[:1] + '***' + name[-1:] if len(name) > 2 else 'Khách hàng'},
                'rating': data['rating'], 'helpfulCount': 0, 'status': 'VISIBLE',
                'reviewText': data.get('reviewText', '').strip(), 'images': data.get('images', [])}
            if item.get('selectedAttributes'):
                document['skuSpecSnapshot'] = item['selectedAttributes']
            self.reviews.insert(document, session)
            summary = self.reviews.rating_summary(product['_id'], session)
            changed = self.products.update_rating_summary(product['_id'], summary, session,
                expected_version=product['version'], now=now)
            if not changed.matched_count:
                raise ConflictError(code='PRODUCT_CHANGED')
            return review_response(document, owner=True)

        try:
            return catalog_transaction(write)
        except DuplicateKeyError:
            raise ConflictError(code='ALREADY_REVIEWED') from None
