"""Bounded retry; callbacks only perform MongoDB operations."""
from pymongo.errors import PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from app.db import get_mongo
from app.errors import ServiceUnavailableError


def catalog_transaction(callback):
    with get_mongo().client.start_session() as session:
        for attempt in range(3):
            try:
                session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority'))
                result = callback(session)
                for commit_attempt in range(3):
                    try:
                        session.commit_transaction()
                        return result
                    except PyMongoError as error:
                        if error.has_error_label('UnknownTransactionCommitResult'):
                            if commit_attempt < 2:
                                continue
                            raise ServiceUnavailableError() from None
                        raise
            except Exception as error:
                if session.in_transaction:
                    session.abort_transaction()
                if isinstance(error, PyMongoError) and error.has_error_label('TransientTransactionError') and attempt < 2:
                    continue
                raise
