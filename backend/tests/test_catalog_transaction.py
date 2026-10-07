"""Retry bounds/ambiguous commit behavior; real rollback/races in test_catalog."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from pymongo.errors import OperationFailure
from app.errors import ConflictError, ServiceUnavailableError
from app.services.catalog_transaction import catalog_transaction


def driver_error(label):
    return OperationFailure('private diagnostic', details={'errorLabels': [label]})


@pytest.fixture
def session(monkeypatch):
    session = MagicMock()
    session.in_transaction = True
    session.__enter__.return_value = session
    mongo = SimpleNamespace(client=SimpleNamespace(start_session=lambda: session))
    monkeypatch.setattr('app.services.catalog_transaction.get_mongo', lambda: mongo)
    return session


def test_transient_callback_retry_then_commit(session):
    callback = MagicMock(side_effect=[driver_error('TransientTransactionError'), 'done'])
    assert catalog_transaction(callback) == 'done'
    assert callback.call_count == 2 and session.start_transaction.call_count == 2
    assert session.abort_transaction.call_count == 1 and session.commit_transaction.call_count == 1


def test_transient_callback_retry_exhaustion(session):
    callback = MagicMock(side_effect=driver_error('TransientTransactionError'))
    with pytest.raises(OperationFailure):
        catalog_transaction(callback)
    assert callback.call_count == session.abort_transaction.call_count == 3


def test_business_error_aborts_without_retry(session):
    callback = MagicMock(side_effect=ConflictError())
    with pytest.raises(ConflictError):
        catalog_transaction(callback)
    assert callback.call_count == session.abort_transaction.call_count == 1
    session.commit_transaction.assert_not_called()


def test_unknown_commit_retries_commit_only(session):
    session.commit_transaction.side_effect = [driver_error('UnknownTransactionCommitResult'), None]
    callback = MagicMock(return_value='done')
    assert catalog_transaction(callback) == 'done'
    assert callback.call_count == 1 and session.commit_transaction.call_count == 2


def test_unknown_commit_exhaustion_never_replays_writes(session):
    session.commit_transaction.side_effect = driver_error('UnknownTransactionCommitResult')
    callback = MagicMock(return_value='done')
    with pytest.raises(ServiceUnavailableError):
        catalog_transaction(callback)
    assert callback.call_count == 1 and session.commit_transaction.call_count == 3


def test_transient_commit_retries_entire_transaction(session):
    session.commit_transaction.side_effect = [driver_error('TransientTransactionError'), None]
    callback = MagicMock(return_value='done')
    assert catalog_transaction(callback) == 'done'
    assert callback.call_count == 2
