"""Update product names in ecommerce_dev to match real products, removing demo artifacts."""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from pymongo import MongoClient
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
sys.stdout.reconfigure(encoding='utf-8')

from app.schemas.catalog_schema import normalize

SPECIFIC_UPDATES = {
    'DEFENSE-07C-FAS': {
        'name': 'Áo thun nam Gigabyte Aorus',
        'brand': 'Gigabyte',
        'slug': 'ao-thun-nam-gigabyte-aorus',
    },
    'DEFENSE-07C-ELE': {
        'name': 'Điện thoại Apple iPhone 5s',
        'brand': 'Apple',
        'slug': 'dien-thoai-apple-iphone-5s',
    },
}

def plan_updates(db):
    updates = []
    prods = list(db.products.find())
    now = datetime.now(timezone.utc)
    
    for p in prods:
        sku = p.get('sku', '')
        old_name = p.get('name', '')
        old_slug = p.get('slug', '')
        old_brand = p.get('brand', '')
        
        doc_changes = {}
        
        if sku in SPECIFIC_UPDATES:
            target = SPECIFIC_UPDATES[sku]
            if old_name != target['name']:
                doc_changes['name'] = target['name']
                doc_changes['nameNormalized'] = normalize(target['name'])
            if old_brand != target['brand']:
                doc_changes['brand'] = target['brand']
                doc_changes['brandNormalized'] = normalize(target['brand'])
            if old_slug != target['slug']:
                doc_changes['slug'] = target['slug']
        elif ' — bản demo 02' in old_name:
            clean_name = old_name.replace(' — bản demo 02', '').strip()
            clean_slug = old_slug.replace('-ban-demo-02', '')
            doc_changes['name'] = clean_name
            doc_changes['nameNormalized'] = normalize(clean_name)
            doc_changes['slug'] = clean_slug
            
        if doc_changes:
            doc_changes['updatedAt'] = now
            doc_changes['version'] = p.get('version', 1) + 1
            updates.append((p['_id'], sku, old_name, doc_changes))
            
    return updates

def execute_updates(db, updates):
    print(f"Applying {len(updates)} updates to database '{db.name}'...")
    with db.client.start_session() as session:
        with session.start_transaction(
            read_concern=ReadConcern('local'),
            write_concern=WriteConcern('majority')
        ):
            for pid, sku, old_name, changes in updates:
                res = db.products.update_one(
                    {'_id': pid},
                    {'$set': changes},
                    session=session
                )
                assert res.matched_count == 1, f"Failed to match product {sku} ({pid})"
    print(f"Transaction committed successfully for '{db.name}'.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Execute updates')
    parser.add_argument('--atlas', action='store_true', help='Also update Atlas novamart_demo')
    args = parser.parse_args()
    
    client = MongoClient('mongodb://127.0.0.1:27017/?replicaSet=rs0')
    dev_db = client['ecommerce_dev']
    
    updates = plan_updates(dev_db)
    print(f"Total products to update: {len(updates)}")
    for pid, sku, old_name, changes in updates[:10]:
        print(f"[{sku}] '{old_name}' -> '{changes.get('name')}' (slug: {changes.get('slug')}, brand: {changes.get('brand', '<keep>')})")
    if len(updates) > 10:
        print(f"... and {len(updates) - 10} more.")
        
    if not args.apply:
        print("\nDry-run completed. Run with --apply to commit changes.")
        return

    execute_updates(dev_db, updates)
    
    if args.atlas:
        import json
        conn_path = ROOT / '.local/atlas-upload/connection.json'
        if conn_path.exists():
            cfg = json.loads(conn_path.read_text(encoding='utf-8'))
            print("\nConnecting to Atlas cluster...")
            atlas_client = MongoClient(cfg['uri'])
            atlas_db = atlas_client[cfg['database']]
            atlas_updates = plan_updates(atlas_db)
            print(f"Atlas products to update: {len(atlas_updates)}")
            execute_updates(atlas_db, atlas_updates)
        else:
            print("Atlas connection.json not found; skipping Atlas update.")

if __name__ == '__main__':
    main()
