"""Report assembly: metadata/empty defaults and calendar buckets only."""
from datetime import datetime, timedelta
from app.errors import ServiceUnavailableError
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard_schema import REPORT_ZONE

ORDER_STATUS_ORDER = ('PENDING', 'CONFIRMED', 'SHIPPING', 'COMPLETED', 'CANCELLED', 'EXPIRED')


def safe_report(value):
    # VND is integer; fail safely instead of silently rounding large aggregates in JS.
    if isinstance(value, dict):
        for item in value.values():
            safe_report(item)
    elif isinstance(value, list):
        for item in value:
            safe_report(item)
    elif isinstance(value, int) and (value < 0 or value > 9007199254740991):
        raise ServiceUnavailableError(message='Kết quả báo cáo vượt giới hạn số nguyên an toàn')
    return value


class DashboardService:
    def __init__(self):
        self.reports = DashboardRepository()

    def summary(self, window):
        sales = self.reports.run('sales-summary', window)
        orders = self.reports.run('order-count', window)
        customers = self.reports.run('customer-count', window)
        return safe_report({
            'totalRevenue': sales[0]['totalRevenue'] if sales else 0,
            'totalProductsSold': sales[0]['totalProductsSold'] if sales else 0,
            'totalOrders': orders[0]['totalOrders'] if orders else 0,
            'totalCustomers': customers[0]['totalCustomers'] if customers else 0,
            **window.metadata(),
        })

    def revenue(self, window):
        rows = self.reports.run(f'revenue-{window.interval}', window)
        pattern = '%Y-%m-%d' if window.interval == 'day' else '%Y-%m'
        buckets = {row['_id'].astimezone(REPORT_ZONE).strftime(pattern): row for row in rows}
        cursor = window.start.astimezone(REPORT_ZONE)
        cursor = datetime(cursor.year, cursor.month, cursor.day if window.interval == 'day' else 1, tzinfo=REPORT_ZONE)
        series = []
        while cursor < window.end:
            label = cursor.strftime(pattern)
            row = buckets.get(label, {})
            series.append({'bucket': label, 'revenue': row.get('revenue', 0), 'orders': row.get('orders', 0)})
            if window.interval == 'day':
                cursor += timedelta(days=1)
            elif cursor.month == 12:
                cursor = cursor.replace(year=cursor.year+1, month=1)
            else:
                cursor = cursor.replace(month=cursor.month+1)
        return safe_report({'series': series, 'interval': window.interval, **window.metadata()})

    def top_products(self, window):
        return safe_report({'items': self.reports.run('top-products', window), **window.metadata()})

    def category_revenue(self, window):
        return safe_report({'items': self.reports.run('category-revenue', window), **window.metadata()})

    def order_status(self, window):
        rows = {item['status']: item['count'] for item in self.reports.run('order-status', window)}
        return safe_report({'items': [{'status': status, 'count': rows.get(status, 0)} for status in ORDER_STATUS_ORDER],
                            'dateBasis': 'createdAt', **window.metadata()})
