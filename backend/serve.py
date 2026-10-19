"""Production entrypoint; supervise explicit API/expiry processes, no seeding."""
import argparse
import os
import sys
from pathlib import Path
from app import create_app
from app.config import load_config
from waitress import serve
from service_supervisor import supervise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--api-only', action='store_true')
    args = parser.parse_args()
    if os.environ.get('APP_ENV') != 'production':
        raise RuntimeError('This entrypoint requires APP_ENV=production')
    config = load_config()
    worker_flag = os.environ.get('PAYMENT_EXPIRY_WORKER_ENABLED', 'false')
    if worker_flag not in {'true', 'false'}:
        raise RuntimeError('PAYMENT_EXPIRY_WORKER_ENABLED must be true/false')
    worker_enabled = config['VNPAY_ENABLED'] or worker_flag == 'true'
    if args.api_only or not worker_enabled:
        app = create_app()
        try:
            serve(app, host=app.config['API_HOST'], port=app.config['API_PORT'], threads=4)
        finally:
            app.extensions['mongo'].close()
    else:
        root = Path(__file__).resolve().parents[1]
        raise SystemExit(supervise({
            'api':[sys.executable, '-X', 'utf8', str(Path(__file__).resolve()), '--api-only'],
            'payment-expiry':[sys.executable, '-X', 'utf8', str(root/'scripts/payment/expire_pending.py')],
        }))


if __name__ == '__main__':
    main()
