"""Record provenance/checksum for the already downloaded public fixture source."""
import hashlib
import json
from pathlib import Path

if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    path = root / 'database/sources/dummyjson-products.json'
    metadata = {'url': 'https://dummyjson.com/products?limit=0', 'documentation': 'https://dummyjson.com/docs/products', 'repository': 'https://github.com/Ovi/DummyJSON', 'softwareLicense': 'MIT (repository); external image rights are not transferred by this project', 'retrievedOn': '2026-10-07', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'sourceProductCount': len(json.loads(path.read_text(encoding='utf-8'))['products']), 'mapping': {'ELECTRONICS': ['smartphones', 'laptops', 'tablets', 'mobile-accessories'], 'FASHION': ['mens-shirts', 'mens-shoes', 'mens-watches', 'womens-dresses', 'womens-shoes', 'womens-bags', 'womens-watches', 'tops', 'sunglasses'], 'HOME_APPLIANCE': ['furniture', 'kitchen-accessories']}, 'normalization': 'Internal schema only; specifications and extra catalog variants are curated demo fixtures, not manufacturer claims. Price uses fixed synthetic USD*25000, not live exchange rate. No external reviews/user fields imported.'}
    (root / 'database/sources/provenance.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print({'sourceProducts': metadata['sourceProductCount'], 'sha256': metadata['sha256']})
