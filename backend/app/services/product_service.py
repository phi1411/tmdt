from datetime import datetime, timezone
from bson import ObjectId
from bson.int64 import Int64
from app.errors import ConflictError, NotFoundError, ValidationError
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.catalog_schema import normalize
from app.schemas.product_schema import PRODUCT_FIELDS, validate_product
from app.services.catalog_transaction import catalog_transaction
from app.utils.ids import parse_object_id


class ProductService:
    def __init__(self):
        self.products = ProductRepository()
        self.categories = CategoryRepository()

    def list(self, query, sort, pagination, public=False):
        return self.products.list(query, sort, pagination, public)

    def detail(self, query, public=False):
        result = self.products.detail(query, public)
        if result is None:
            raise NotFoundError()
        return result

    def guard_category(self, category_id, product_type, now, session):
        if self.categories.guard_active(category_id, product_type, now, session) is None:
            raise ConflictError(code='CATEGORY_UNAVAILABLE', message='Danh mục không tồn tại, đã ẩn hoặc không phù hợp loại sản phẩm')

    def create(self, payload):
        validate_product(payload)
        now = datetime.now(timezone.utc)
        product_id = ObjectId()
        category_id = parse_object_id(payload['categoryId'], 'categoryId')
        document = {'_id': product_id, 'schemaVersion': 1, 'createdAt': now, 'updatedAt': now, 'version': 1,
            **payload, 'categoryId': category_id, 'price': Int64(payload['price']),
            'nameNormalized': normalize(payload['name']), 'brandNormalized': normalize(payload['brand'])}

        def write(session):
            self.guard_category(category_id, payload['productType'], now, session)
            self.products.insert(document, session)
        catalog_transaction(write)
        return self.detail({'_id': product_id})

    def update(self, product_id, payload):
        changes = {k: v for k, v in payload.items() if k != 'expectedVersion'}
        if not changes:
            raise ValidationError(details=[{'field': '$', 'reason': 'Cần ít nhất một trường cập nhật'}])
        now = datetime.now(timezone.utc)

        def write(session):
            current = self.products.find(product_id, session)
            if current is None:
                raise NotFoundError()
            if current['version'] != payload['expectedVersion']:
                raise ConflictError(code='PRODUCT_CHANGED')
            if current['version'] >= 2147483647:
                raise ConflictError(code='VERSION_LIMIT')
            if current['status'] == 'ARCHIVED' and changes != {'status': 'ACTIVE'}:
                raise ConflictError(code='INVALID_TRANSITION')
            if changes.get('productType', current['productType']) != current['productType'] and 'attributes' not in changes:
                raise ValidationError(details=[{'field': 'attributes', 'reason': 'Đổi loại cần gửi thuộc tính tương hợp'}])
            fields = {**{k: current[k] for k in PRODUCT_FIELDS}, **changes}
            if 'price' not in changes:
                fields['price'] = int(fields['price'])
            fields['categoryId'] = str(fields['categoryId'])
            validate_product(fields)
            category_id = parse_object_id(fields['categoryId'], 'categoryId')
            category = self.categories.find({'_id': category_id}, session)
            if category is None or category['productType'] != fields['productType']:
                raise ConflictError(code='CATEGORY_UNAVAILABLE')
            moved = category_id != current['categoryId'] or fields['productType'] != current['productType']
            published = fields['status'] == 'ACTIVE' and current['status'] != 'ACTIVE'
            if moved or published:
                self.guard_category(category_id, fields['productType'], now, session)
            stored = dict(changes)
            if 'categoryId' in stored:
                stored['categoryId'] = category_id
            if 'price' in stored:
                stored['price'] = Int64(stored['price'])
            if 'name' in stored:
                stored['nameNormalized'] = normalize(stored['name'])
            if 'brand' in stored:
                stored['brandNormalized'] = normalize(stored['brand'])
            result = self.products.patch(product_id, payload['expectedVersion'], stored, now, session)
            if result is None:
                raise ConflictError(code='PRODUCT_CHANGED')
            return result
        return self.with_category(catalog_transaction(write))

    def with_category(self, product):
        category = self.categories.find({'_id': product['categoryId']})
        product['category'] = {k: category[k] for k in ('_id', 'name', 'slug', 'productType')} if category else None
        return product

    def archive(self, product_id, version):
        now = datetime.now(timezone.utc)

        def write(session):
            current = self.products.find(product_id, session)
            if current is None:
                raise NotFoundError()
            if current['status'] == 'ARCHIVED':
                return
            if current['version'] >= 2147483647:
                raise ConflictError(code='VERSION_LIMIT')
            if self.products.patch(product_id, version, {'status': 'ARCHIVED'}, now, session) is None:
                raise ConflictError(code='PRODUCT_CHANGED')
        catalog_transaction(write)
