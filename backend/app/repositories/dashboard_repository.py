"""Execute canonical EJSON pipelines; never recalculate sales in Python."""
import copy
from functools import lru_cache
from pathlib import Path
from bson import json_util
from app.db import get_db

PIPELINE_ROOT = Path(__file__).resolve().parents[3] / 'database' / 'aggregations'
PIPELINES = frozenset({'revenue-day', 'revenue-month', 'top-products', 'category-revenue',
                      'sales-summary', 'order-count', 'order-status', 'customer-count'})


@lru_cache(maxsize=8)
def canonical_pipeline(name):
    if name not in PIPELINES:
        raise ValueError('Unknown canonical report')
    return json_util.loads((PIPELINE_ROOT / f'{name}.json').read_text(encoding='utf-8'),
                           json_options=json_util.JSONOptions(tz_aware=True))


class DashboardRepository:
    def __init__(self):
        self.database = get_db()

    def pipeline(self, name, window):
        pipeline = copy.deepcopy(canonical_pipeline(name))
        if name != 'customer-count':
            date_field = 'createdAt' if name in {'order-count', 'order-status'} else 'completedAt'
            pipeline[0]['$match'][date_field] = {'$gte': window.start, '$lt': window.end}
        return pipeline

    def run(self, name, window):
        collection = self.database.users if name == 'customer-count' else self.database.orders
        return list(collection.aggregate(self.pipeline(name, window), maxTimeMS=10000, allowDiskUse=False))
