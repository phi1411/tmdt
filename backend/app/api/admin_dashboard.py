"""Admin-only report endpoints with bounded allowlisted query inputs."""
from flask import Blueprint, request
from app.auth import require_roles
from app.schemas.dashboard_schema import report_query
from app.services.dashboard_service import DashboardService
from app.utils.responses import success

admin_dashboard_blueprint = Blueprint('admin_dashboard', __name__)


@admin_dashboard_blueprint.get('/admin/dashboard/summary')
@require_roles('ADMIN')
def summary():
    return success(DashboardService().summary(report_query(request.args)))


@admin_dashboard_blueprint.get('/admin/dashboard/revenue')
@require_roles('ADMIN')
def revenue():
    return success(DashboardService().revenue(report_query(request.args, revenue=True)))


@admin_dashboard_blueprint.get('/admin/dashboard/top-products')
@require_roles('ADMIN')
def top_products():
    return success(DashboardService().top_products(report_query(request.args)))


@admin_dashboard_blueprint.get('/admin/dashboard/category-revenue')
@require_roles('ADMIN')
def category_revenue():
    return success(DashboardService().category_revenue(report_query(request.args)))


@admin_dashboard_blueprint.get('/admin/dashboard/order-status')
@require_roles('ADMIN')
def order_status():
    return success(DashboardService().order_status(report_query(request.args)))
