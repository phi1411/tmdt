from app.repositories.review_repository import ReviewRepository
from app.repositories.product_repository import ProductRepository


class ReviewService:
    def __init__(self):
        self.reviews = ReviewRepository()
        self.products = ProductRepository()

    def get_product_reviews(self, product_id, limit=20):
        items = self.reviews.list_by_product(product_id, limit=limit)
        product = self.products.find(product_id, None)
        stats = product.get('ratingSummary') if product else None
        return items, stats
