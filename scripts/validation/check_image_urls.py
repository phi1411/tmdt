"""Optional representative HEAD checks; never downloads catalog media."""
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'db'))
from common import connection, write_ejson

if __name__ == '__main__':
    client, db = connection()
    checks = []
    try:
        for kind in ('ELECTRONICS', 'FASHION', 'HOME_APPLIANCE'):
            product = db.products.find_one({'productType': kind}, sort=[('sku', 1)])
            url = product['images'][0]
            result = {'productId': product['_id'], 'productType': kind, 'url': url, 'method': 'HEAD'}
            try:
                with urlopen(Request(url, method='HEAD', headers={'User-Agent': 'tmdt-development-fixture-check'}), timeout=20) as response:
                    result.update(status=response.status, contentType=response.headers.get('Content-Type'))
            except (URLError, HTTPError) as exc:
                result.update(status='UNAVAILABLE', error=str(exc))
            checks.append(result)
        write_ejson('database/evidence/image-url-checks.json', {'checks': checks, 'scope': '3 representative URLs only; all180 Products separately checked nonempty HTTPS, not all media fetched'})
        print(checks)
    finally:
        client.close()
