from datetime import datetime, timezone
from bson import ObjectId
from app.errors import ConflictError, NotFoundError
from app.repositories.review_repository import ReviewRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.review_schema import review_response
from app.utils.ids import parse_object_id


class ReviewService:
    def __init__(self):
        self.reviews = ReviewRepository()
        self.products = ProductRepository()
        self.orders = OrderRepository()

    def get_product_reviews(self, product_id, limit=20):
        items = self.reviews.list_by_product(product_id, limit=limit)
        product = self.products.find(product_id, None)
        stats = product.get('ratingSummary') if product else None
        return items, stats

    def create_review(self, user, identifier, data):
        if ObjectId.is_valid(identifier):
            product = self.products.find(ObjectId(identifier), None)
        else:
            product = self.products.collection.find_one({'slug': identifier, 'status': 'ACTIVE'})
        if not product:
            raise NotFoundError(message='Không tìm thấy sản phẩm')

        order_id = parse_object_id(data['orderId'].lower(), 'orderId')
        order = self.orders.find(user['_id'], order_id)
        if not order:
            raise NotFoundError(message='Không tìm thấy đơn hàng')

        if order.get('orderStatus') != 'COMPLETED':
            raise ConflictError(code='ORDER_NOT_COMPLETED', message='Chỉ có thể đánh giá đơn hàng đã hoàn tất')

        items = order.get('items', [])
        matching_item = next((it for it in items if it.get('productId') == product['_id']), None)
        if not matching_item:
            raise ConflictError(code='PRODUCT_NOT_IN_ORDER', message='Sản phẩm không thuộc đơn hàng này')

        existing = self.reviews.find_user_review(user['_id'], order['_id'], product['_id'])
        if existing:
            raise ConflictError(code='ALREADY_REVIEWED', message='Bạn đã đánh giá sản phẩm này cho đơn hàng này rồi')

        now = datetime.now(timezone.utc)
        display_name = (user.get('name') or order.get('customerSnapshot', {}).get('name') or 'Khách hàng')[:100]

        review_doc = {
            '_id': ObjectId(),
            'schemaVersion': 1,
            'createdAt': now,
            'updatedAt': now,
            'productId': product['_id'],
            'orderId': order['_id'],
            'userId': user['_id'],
            'orderCode': order.get('orderCode', ''),
            'userSnapshot': {
                'displayName': display_name,
            },
            'rating': int(data['rating']),
            'helpfulCount': 0,
            'status': 'VISIBLE',
        }
        if matching_item.get('selectedAttributes'):
            review_doc['skuSpecSnapshot'] = matching_item['selectedAttributes']
        if 'reviewText' in data and data['reviewText'] is not None:
            review_doc['reviewText'] = str(data['reviewText'])
        if 'images' in data and data['images'] is not None:
            review_doc['images'] = list(data['images'])

        self.reviews.insert(review_doc)

        # Update product ratingSummary
        rating_summary = product.get('ratingSummary') or {}
        old_total = rating_summary.get('totalReviews', 0)
        old_breakdown = rating_summary.get('starsBreakdown') or {}
        new_breakdown = {str(i): int(old_breakdown.get(str(i), 0)) for i in range(1, 6)}
        new_breakdown[str(data['rating'])] += 1
        new_total = old_total + 1
        total_stars = sum(int(k) * v for k, v in new_breakdown.items())
        new_average = round(float(total_stars) / new_total, 1)

        updated_summary = {
            'averageRating': float(new_average),
            'totalReviews': int(new_total),
            'starsBreakdown': new_breakdown,
        }
        self.products.update_rating_summary(product['_id'], updated_summary)

        return review_response(review_doc)
