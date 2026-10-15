"""Apply the six locked validators and 14 selected indexes to a local dev DB."""
import argparse
from common import connection, apply_foundation, selected_indexes

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='ecommerce_dev')
    args = parser.parse_args()
    client, db = connection(args.database, claim=True)
    try:
        apply_foundation(db)
        print(f'{db.name}: 7 validators applied; {len(selected_indexes())} declared indexes')
    finally:
        client.close()
