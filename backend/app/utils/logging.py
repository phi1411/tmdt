"""Allowlisted JSON logs. No bodies, query strings, headers, exception messages."""
import json
import logging
import sys
from datetime import datetime, timezone


class SafeJSONFormatter(logging.Formatter):
    def format(self, record):
        event = {
            'time': datetime.now(timezone.utc).isoformat(), 'level': record.levelname,
            'event': getattr(record, 'event', 'application.log'),
        }
        for key in ('request_id', 'method', 'endpoint', 'status', 'duration_ms', 'error_type',
                    'actor_id', 'order_id', 'action', 'order_status', 'order_version', 'previous_order_status'):
            if hasattr(record, key):
                event[key] = getattr(record, key)
        if record.exc_info and record.exc_info[2]:
            # Stack location is useful; exception text/locals can contain secrets.
            trace = record.exc_info[2]
            frames = []
            while trace:
                frames.append({'module': trace.tb_frame.f_globals.get('__name__', ''), 'function': trace.tb_frame.f_code.co_name, 'line': trace.tb_lineno})
                trace = trace.tb_next
            event['frames'] = frames
        return json.dumps(event, ensure_ascii=True)


def configure_logging(app):
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(SafeJSONFormatter())
    app.logger.handlers = [handler]
    app.logger.propagate = False
    app.logger.setLevel(app.config['LOG_LEVEL'])
    # Library debug logging can expose command documents and connection details.
    logging.getLogger('pymongo').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('flask_cors').setLevel(logging.WARNING)


def log_failure(app, event, error, request_id=None, method=None, endpoint=None):
    app.logger.error('failure', extra={'event': event, 'error_type': type(error).__name__, 'request_id': request_id, 'method': method, 'endpoint': endpoint}, exc_info=(type(error), error, error.__traceback__))
