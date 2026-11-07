import threading

import pytest

from homepage.fedi import views


def test_timed_out_lookups_hold_capacity_until_lookup_exits(monkeypatch):
    slots = threading.BoundedSemaphore(2)
    monkeypatch.setattr(views, "_resolver_slots", slots, raising=False)
    release = threading.Event()
    workers = []

    def blocked_resolver(*args, **kwargs):
        workers.append(threading.current_thread())
        assert release.wait(5)
        return ["synthetic address"]

    monkeypatch.setattr(views.socket, "getaddrinfo", blocked_resolver)
    try:
        for _ in range(5):
            with pytest.raises(views.UpstreamTimeout):
                views._resolve("resolver.invalid", 443, 0.02)
        assert len(workers) == 2
        assert all(worker.is_alive() for worker in workers)
        # Existing workers must release the semaphore they actually acquired.
        monkeypatch.setattr(views, "_resolver_slots", threading.BoundedSemaphore(1))
    finally:
        release.set()
        for worker in workers:
            worker.join(2)
            assert not worker.is_alive()
    assert slots.acquire(blocking=False)
    assert slots.acquire(blocking=False)
    slots.release()
    slots.release()
    assert views._resolve("resolver.invalid", 443, 1) == ["synthetic address"]


@pytest.mark.parametrize("start_error", [RuntimeError, MemoryError])
def test_resolver_errors_and_failed_thread_start_release_capacity(monkeypatch, start_error):
    slots = threading.BoundedSemaphore(1)
    monkeypatch.setattr(views, "_resolver_slots", slots, raising=False)

    def failed_resolver(*args, **kwargs):
        raise OSError("synthetic DNS error")

    monkeypatch.setattr(views.socket, "getaddrinfo", failed_resolver)
    for _ in range(2):
        with pytest.raises(views.UpstreamError):
            views._resolve("resolver.invalid", 443, 1)
    with monkeypatch.context() as patch:

        def failed_start(self):
            raise start_error("synthetic start failure")

        patch.setattr(threading.Thread, "start", failed_start)
        with pytest.raises(views.UpstreamError if start_error is RuntimeError else MemoryError):
            views._resolve("resolver.invalid", 443, 1)
    monkeypatch.setattr(views.socket, "getaddrinfo", lambda *args, **kwargs: [])
    assert views._resolve("resolver.invalid", 443, 1) == []
