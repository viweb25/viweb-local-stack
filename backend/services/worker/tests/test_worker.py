from worker.app import app, ping


def test_smoke_task_without_broker():
    app.conf.task_always_eager = True
    assert ping.apply().get() == {"status": "ok", "service": "worker"}
