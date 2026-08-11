from app.tasks import cleanup_auth_sessions, cleanup_outbox, dispatch_outbox
from app.tiq import broker


def test_broker_allows_indefinite_blocking_queue_reads():
    assert broker.connection_pool.connection_kwargs["socket_timeout"] is None


def test_background_task_schedules_are_registered():
    assert dispatch_outbox.labels["schedule"] == [{"cron": "* * * * *"}]
    assert cleanup_outbox.labels["schedule"] == [{"cron": "0 3 * * *"}]
    assert cleanup_auth_sessions.labels["schedule"] == [{"cron": "15 3 * * *"}]
