"""Local development entrypoint. Factory creation is explicit, not import-time."""
from app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(host=app.config['API_HOST'], port=app.config['API_PORT'], debug=False, use_reloader=False)
