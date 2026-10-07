"""Register only implemented versioned HTTP features."""
from app.api.health import health_blueprint
from app.api.categories import categories_blueprint
from app.api.products import products_blueprint
from app.api.admin_products import admin_products_blueprint
from app.api.auth import auth_blueprint
from app.api.users import users_blueprint
from app.api.admin_users import admin_users_blueprint


def register_blueprints(app):
    app.register_blueprint(health_blueprint, url_prefix=app.config['API_PREFIX'])
    for blueprint in (categories_blueprint, products_blueprint, admin_products_blueprint):
        app.register_blueprint(blueprint, url_prefix=app.config['API_PREFIX'])
    for blueprint in (auth_blueprint, users_blueprint, admin_users_blueprint):
        app.register_blueprint(blueprint, url_prefix=app.config['API_PREFIX'])
