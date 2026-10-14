"""Register only implemented versioned HTTP features."""
from app.api.health import health_blueprint
from app.api.categories import categories_blueprint
from app.api.products import products_blueprint
from app.api.admin_products import admin_products_blueprint
from app.api.auth import auth_blueprint
from app.api.users import users_blueprint
from app.api.admin_users import admin_users_blueprint
from app.api.cart import cart_blueprint
from app.api.checkout import checkout_blueprint
from app.api.orders import orders_blueprint
from app.api.payments import payments_blueprint
from app.api.admin_orders import admin_orders_blueprint
from app.api.admin_dashboard import admin_dashboard_blueprint


def register_blueprints(app):
    app.register_blueprint(health_blueprint, url_prefix=app.config['API_PREFIX'])
    for blueprint in (categories_blueprint, products_blueprint, admin_products_blueprint):
        app.register_blueprint(blueprint, url_prefix=app.config['API_PREFIX'])
    for blueprint in (auth_blueprint, users_blueprint, admin_users_blueprint):
        app.register_blueprint(blueprint, url_prefix=app.config['API_PREFIX'])
    for blueprint in (cart_blueprint, checkout_blueprint, orders_blueprint):
        app.register_blueprint(blueprint, url_prefix=app.config['API_PREFIX'])
    app.register_blueprint(payments_blueprint, url_prefix=app.config['API_PREFIX'])
    for blueprint in (admin_orders_blueprint, admin_dashboard_blueprint):
        app.register_blueprint(blueprint, url_prefix=app.config['API_PREFIX'])
