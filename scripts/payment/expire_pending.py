"""Explicit VNPAY expiry worker. No TTL deletion, seed/reset or external requests."""
import argparse
import json
import sys
from pathlib import Path
from threading import Event

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app import create_app
from app.services.payment_service import PaymentService
from app.utils.logging import log_failure


def main():
    parser = argparse.ArgumentParser(description='Expire eligible pending VNPAY holds atomically')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    app = create_app()
    stop = Event()
    try:
        with app.app_context():
            while True:
                try:
                    result = PaymentService().expire_due()
                except Exception as error:
                    log_failure(app, 'payment.expiry_scan_failed', error)
                    result = {'scanned': 0, 'expired': 0, 'failed': 1}
                print(json.dumps(result), flush=True)
                if args.once:
                    if result['failed']:
                        raise SystemExit(1)
                    break
                stop.wait(app.config['PAYMENT_EXPIRY_POLL_SECONDS'])
    except KeyboardInterrupt:
        pass
    finally:
        app.extensions['mongo'].close()


if __name__ == '__main__':
    main()
