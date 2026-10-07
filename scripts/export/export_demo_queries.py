"""Render canonical pipelines into a reproducible mongosh/Compass demo script."""
import json
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'db'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'seed'))
from common import ROOT, pipeline
from seed import START, ANCHOR

def javascript(value):
    if isinstance(value, datetime):
        return 'ISODate(' + json.dumps(value.isoformat().replace('+00:00', 'Z')) + ')'
    if isinstance(value, list):
        return '[\n' + ',\n'.join(javascript(v) for v in value) + '\n]'
    if isinstance(value, dict):
        return '{' + ', '.join(json.dumps(k) + ': ' + javascript(v) for k, v in value.items()) + '}'
    return json.dumps(value, ensure_ascii=False)

if __name__ == '__main__':
    lines = ['// Generated from canonical artifacts. MongoDB aggregation outputs are verified via PyMongo.', '// Optional mongosh/Compass shell demo; shell UI rehearsal is deferred.', 'const demoDB = db.getSiblingDB("ecommerce_dev");', 'printjson(demoDB.products.countDocuments({}));', 'printjson(demoDB.orders.countDocuments({}));', 'printjson(demoDB.products.find({sku: {$in: ["DEMO-ELE-001", "DEMO-FAS-001", "DEMO-HOM-001"]}}).toArray());', 'printjson(demoDB.orders.findOne({orderCode: "DEMO-2026-0001"}));']
    for name in ['revenue-day', 'revenue-month', 'top-products', 'category-revenue', 'sales-summary', 'order-count', 'order-status', 'customer-count']:
        collection = 'users' if name == 'customer-count' else 'orders'
        lines.extend([f'// {name}: completedAt revenue cohort; createdAt for order counts.', f'printjson(demoDB.{collection}.aggregate({javascript(pipeline(name, START, ANCHOR))}).toArray());'])
    lines.extend(['printjson(demoDB.products.getIndexes());', 'printjson(demoDB.orders.getIndexes());', 'const category = demoDB.categories.findOne({productType: "ELECTRONICS"});', 'printjson(demoDB.products.find({status: "ACTIVE", categoryId: category._id, price: {$gte: NumberLong("1000000"), $lte: NumberLong("20000000")}}).sort({price: 1, _id: 1}).limit(10).explain("executionStats"));'])
    (ROOT / 'database/evidence/demo-queries.mongodb.js').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print('Generated database/evidence/demo-queries.mongodb.js from canonical pipelines.')
