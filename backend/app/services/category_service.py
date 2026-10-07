from datetime import datetime, timezone
from bson import ObjectId
from app.errors import ConflictError, NotFoundError, ValidationError
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.category_schema import CATEGORY_FIELDS, validate_category
from app.services.catalog_transaction import catalog_transaction


class CategoryService:
    def __init__(self):
        self.categories = CategoryRepository()
        self.products = ProductRepository()

    def list(self, query, pagination):
        return self.categories.list(query, pagination)

    def detail(self, query):
        result = self.categories.find(query)
        if result is None:
            raise NotFoundError()
        return result

    def create(self, payload):
        fields = {'description': '', 'status': 'ACTIVE', **payload}
        validate_category(fields)
        now = datetime.now(timezone.utc)
        document = {'_id': ObjectId(), 'schemaVersion': 1, 'createdAt': now, 'updatedAt': now, 'version': 1, **fields}
        self.categories.insert(document)
        return self.detail({'_id': document['_id']})

    def update(self, category_id, payload):
        changes = {k: v for k, v in payload.items() if k != 'expectedVersion'}
        if not changes:
            raise ValidationError(details=[{'field': '$', 'reason': 'Cần ít nhất một trường cập nhật'}])
        now = datetime.now(timezone.utc)

        def write(session):
            current = self.categories.find({'_id': category_id}, session)
            if current is None:
                raise NotFoundError()
            if current['version'] >= 2147483647:
                raise ConflictError(code='VERSION_LIMIT')
            validate_category({**{k: current[k] for k in CATEGORY_FIELDS}, **changes})
            changed = self.categories.patch({'_id': category_id, 'version': payload['expectedVersion']}, changes, now, session)
            if changed is None:
                raise ConflictError(code='CATEGORY_CHANGED')
            if current['productType'] != changed['productType'] and self.products.referenced(category_id, session):
                raise ConflictError(code='CATEGORY_IN_USE')
            return changed
        return catalog_transaction(write)

    def delete(self, category_id, version):
        now = datetime.now(timezone.utc)

        def write(session):
            current = self.categories.find({'_id': category_id}, session)
            if current is None:
                raise NotFoundError()
            if current['version'] >= 2147483647:
                raise ConflictError(code='VERSION_LIMIT')
            if self.categories.patch({'_id': category_id, 'version': version}, {}, now, session) is None:
                raise ConflictError(code='CATEGORY_CHANGED')
            if self.products.referenced(category_id, session):
                raise ConflictError(code='CATEGORY_IN_USE')
            self.categories.delete(category_id, session)
        catalog_transaction(write)
