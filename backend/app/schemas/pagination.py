"""Locked page/pageSize offset pagination; metadata shared by future APIs."""
from dataclasses import dataclass
import re
from app.errors import BadRequestError, ValidationError


def query_integer(value, field, minimum, maximum=None):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]+', value) or len(value) > 15:
        raise BadRequestError(details=[{'field': field, 'reason': 'Tham số phải là số nguyên không dấu'}])
    result = int(value)
    if result < minimum or (maximum is not None and result > maximum):
        raise ValidationError(details=[{'field': field, 'reason': 'Giá trị ngoài giới hạn cho phép'}])
    return result


@dataclass(frozen=True)
class Pagination:
    page: int = 1
    page_size: int = 20

    @classmethod
    def from_query(cls, values):
        return cls(
            query_integer(values.get('page', '1'), 'page', 1),
            query_integer(values.get('pageSize', '20'), 'pageSize', 1, 100),
        )

    @property
    def skip(self):
        return (self.page - 1) * self.page_size

    def metadata(self, total):
        if type(total) is not int or total < 0:
            raise ValueError('Total must be a non-negative integer')
        return {'page': self.page, 'pageSize': self.page_size, 'total': total, 'totalPages': (total + self.page_size - 1) // self.page_size}
