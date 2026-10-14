"""Production WSGI entrypoint; no seeding, schema mutation or expiry worker."""
import os
from app import create_app
from waitress import serve


def main():
    if os.environ.get('APP_ENV') != 'production':
        raise RuntimeError('This entrypoint requires APP_ENV=production')
    app = create_app()
    serve(app, host=app.config['API_HOST'], port=app.config['API_PORT'], threads=4)


if __name__ == '__main__':
    main()
