"""Bounded UTC report windows and stable metadata from the locked contract."""
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.errors import ValidationError
from app.schemas.validation import single_query_values

REPORT_TIMEZONE = 'Asia/Ho_Chi_Minh'
REPORT_ZONE = ZoneInfo(REPORT_TIMEZONE)
REVENUE_BASIS = 'PAID_COMPLETED_MERCHANDISE'


def utc_date(value, field):
    try:
        if not isinstance(value, str) or not re.fullmatch(
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)', value,
        ):
            raise ValueError()
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.year > 9998:
            raise ValueError()
        return parsed
    except (ValueError, TypeError):
        raise ValidationError(details=[{'field': field, 'reason': 'Cần ISO UTC hợp lệ, năm tối đa 9998'}]) from None


@dataclass(frozen=True)
class ReportWindow:
    start: datetime
    end: datetime
    interval: str = 'day'

    def metadata(self):
        return {'currency': 'VND', 'timezone': REPORT_TIMEZONE, 'from': self.start, 'to': self.end,
                'revenueBasis': REVENUE_BASIS, 'fetchedAt': datetime.now(timezone.utc)}


def report_query(args, revenue=False):
    values = single_query_values(args, {'from', 'to', *({'interval'} if revenue else set())})
    for field in ('from', 'to'):
        if field not in values:
            raise ValidationError(details=[{'field': field, 'reason': 'Thiếu trường bắt buộc'}])
    start, end = utc_date(values['from'], 'from'), utc_date(values['to'], 'to')
    if start >= end or end - start > timedelta(days=366):
        raise ValidationError(details=[{'field': 'to', 'reason': 'Cần from < to và khoảng tối đa 366 ngày'}])
    interval = values.get('interval', 'day')
    if interval not in {'day', 'month'}:
        raise ValidationError(details=[{'field': 'interval', 'reason': 'Chỉ hỗ trợ day hoặc month'}])
    return ReportWindow(start, end, interval)
