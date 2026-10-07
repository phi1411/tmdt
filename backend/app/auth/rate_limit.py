"""Bounded, thread-safe local auth limits; no raw email/IP stored or logged."""
from hashlib import sha256
import hmac
import secrets
from threading import Lock
from time import monotonic
from werkzeug.exceptions import TooManyRequests


class AuthRateLimiter:
    WINDOW_SECONDS = 60
    MAX_BUCKETS = 10000

    def __init__(self, clock=monotonic):
        self.clock = clock
        self.secret = secrets.token_bytes(32)
        self.buckets = {}
        self.lock = Lock()

    def check(self, operation, ip, email=None, account_only=False):
        limits = [] if account_only else [(f'{operation}:ip:{ip}', 10 if operation == 'register' else 30)]
        if email is not None:
            limits.append((f'{operation}:account:{email}', 10))
        keys = [(hmac.new(self.secret, value.encode(), sha256).digest(), limit) for value, limit in limits]
        with self.lock:
            now = self.clock()
            self.buckets = {key: bucket for key, bucket in self.buckets.items() if bucket[0] > now}
            for key, limit in keys:
                expiry, count = self.buckets.get(key, (now + self.WINDOW_SECONDS, 0))
                if count >= limit:
                    raise TooManyRequests(retry_after=max(1, int(expiry - now) + 1))
            if len(self.buckets) + sum(key not in self.buckets for key, _ in keys) > self.MAX_BUCKETS:
                raise TooManyRequests(retry_after=self.WINDOW_SECONDS)
            for key, _ in keys:
                expiry, count = self.buckets.get(key, (now + self.WINDOW_SECONDS, 0))
                self.buckets[key] = (expiry, count + 1)
