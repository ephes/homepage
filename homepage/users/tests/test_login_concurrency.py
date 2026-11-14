"""Independent workers sharing the same production-style file cache."""

import multiprocessing
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import patch

import pytest
from django.core.cache import caches
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from homepage.users import login_throttle as module


def record_in_worker(cache_settings, barrier):
    with override_settings(CACHES=cache_settings):
        module.LoginFailureThrottle.THROTTLE_RATES = {"admin_login_username": "8/hour"}
        throttle = module.AdminLoginUsernameThrottle("synthetic-user")
        original_load = throttle._load

        def slow_load():
            original_load()
            # Widen the read/replace race while every process starts together.
            time.sleep(0.05)

        throttle._load = slow_load
        barrier.wait(timeout=20)
        throttle.record_failure()


def test_file_cache_failure_updates_are_atomic_across_processes(tmp_path, monkeypatch):
    cache_settings = {
        module.THROTTLE_CACHE_ALIAS: {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": str(tmp_path),
        },
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    }
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(8)
    processes = [ctx.Process(target=record_in_worker, args=(cache_settings, barrier)) for _ in range(8)]
    for process in processes:
        process.start()
    try:
        for process in processes:
            process.join(timeout=30)
            assert process.exitcode == 0
        monkeypatch.setattr(module.LoginFailureThrottle, "THROTTLE_RATES", {"admin_login_username": "8/hour"})
        with override_settings(CACHES=cache_settings):
            throttle = module.AdminLoginUsernameThrottle("synthetic-user")
            assert throttle.is_blocked()
            assert len(throttle.history) == 8
            throttle.record_failure()
            assert len(caches[module.THROTTLE_CACHE_ALIAS].get(throttle.key)) == 8
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
            process.join(timeout=5)


@pytest.fixture
def one_attempt(monkeypatch):
    monkeypatch.setattr(
        module.LoginFailureThrottle,
        "THROTTLE_RATES",
        {"admin_login_client": "1/hour", "admin_login_username": "1/hour"},
    )
    caches["default"].clear()
    yield
    caches["default"].clear()


@pytest.mark.parametrize("shared", ["client", "username"])
def test_one_slot_admits_only_one_concurrent_authentication(one_attempt, shared):
    start = Barrier(8)
    entered = Event()
    release = Event()
    calls = []

    @module.throttle_failed_logins
    def authenticate(request):
        calls.append(request)
        entered.set()
        assert release.wait(timeout=15)
        return HttpResponse()

    def send(index):
        request = RequestFactory().post(
            "/login/",
            {"username": "same" if shared == "username" else f"user-{index}"},
            REMOTE_ADDR="203.0.113.1" if shared == "client" else f"203.0.113.{index + 1}",
        )
        start.wait(timeout=15)
        return authenticate(request).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(send, index) for index in range(8)]
        try:
            assert entered.wait(timeout=15)
            # All other requests must settle while the admitted backend is held.
            deadline = time.monotonic() + 3
            while sum(f.done() for f in futures) < 7 and time.monotonic() < deadline:
                time.sleep(0.01)
            assert sum(f.done() for f in futures) == 7
        finally:
            release.set()
        assert sorted(f.result(timeout=15) for f in futures) == [200] + [429] * 7
    assert len(calls) == 1


def test_success_and_exception_release_admission(one_attempt):
    def request():
        return RequestFactory().post("/login/", {"username": "same"})

    @module.throttle_failed_logins
    def success(req):
        setattr(req, module.LOGGED_IN_ATTR, True)
        return HttpResponse()

    for _ in range(3):
        assert success(request()).status_code == 200

    @module.throttle_failed_logins
    def broken(req):
        raise RuntimeError("synthetic failure")

    with pytest.raises(RuntimeError):
        broken(request())
    for throttle in [
        module.AdminLoginClientThrottle(request()),
        module.AdminLoginUsernameThrottle("same"),
    ]:
        assert caches["default"].get(throttle.key + "_inflight") is None
        assert len(caches["default"].get(throttle.key)) == 1
    # Expire the failure window; an orphaned reservation must not remain.
    with patch.object(module.LoginFailureThrottle, "timer", return_value=time.time() + 3601):
        assert success(request()).status_code == 200


def authenticate_in_worker(cache_settings, start, release, statuses, index, shared):
    with override_settings(CACHES=cache_settings):
        module.LoginFailureThrottle.THROTTLE_RATES = {"admin_login_client": "1/hour", "admin_login_username": "1/hour"}

        @module.throttle_failed_logins
        def authenticate(request):
            statuses.put("entered")
            assert release.wait(timeout=20)
            setattr(request, module.LOGGED_IN_ATTR, True)
            return HttpResponse()

        request = RequestFactory().post(
            "/login/",
            {"username": "same" if shared == "username" else f"user-{index}"},
            REMOTE_ADDR="203.0.113.1" if shared == "client" else f"203.0.113.{index + 1}",
        )
        start.wait(timeout=20)
        statuses.put(authenticate(request).status_code)


@pytest.mark.parametrize("shared", ["client", "username"])
def test_file_cache_inflight_admission_across_processes(tmp_path, shared):
    cache_settings = {
        "default": {"BACKEND": "django.core.cache.backends.filebased.FileBasedCache", "LOCATION": str(tmp_path)}
    }
    ctx = multiprocessing.get_context("spawn")
    start, release, statuses = ctx.Barrier(8), ctx.Event(), ctx.Queue()
    processes = [
        ctx.Process(target=authenticate_in_worker, args=(cache_settings, start, release, statuses, i, shared))
        for i in range(8)
    ]
    for process in processes:
        process.start()
    try:
        results = [statuses.get(timeout=20) for _ in range(8)]
        assert results.count("entered") == 1
        assert results.count(429) == 7
        release.set()
        assert statuses.get(timeout=20) == 200
        for process in processes:
            process.join(timeout=20)
            assert process.exitcode == 0
    finally:
        release.set()
        for process in processes:
            if process.is_alive():
                process.terminate()
            process.join(timeout=5)
        statuses.close()
        statuses.join_thread()


def test_expired_reservation_and_late_completion_preserve_new_owner(one_attempt):
    first = module.AdminLoginUsernameThrottle("same")
    assert first.reserve()
    second = module.AdminLoginUsernameThrottle("same")
    with patch.object(module.LoginFailureThrottle, "timer", return_value=first.now + module.ADMISSION_SECONDS + 1):
        assert second.reserve()
        first.finish()
        assert not module.AdminLoginUsernameThrottle("same").reserve()
        second.finish()
        third = module.AdminLoginUsernameThrottle("same")
        assert third.reserve()
        third.finish()


def test_username_refusal_releases_client_and_exception_counts_failure(one_attempt):
    username = module.AdminLoginUsernameThrottle("blocked")
    username.record_failure()

    @module.throttle_failed_logins
    def successful(request):
        setattr(request, module.LOGGED_IN_ATTR, True)
        return HttpResponse()

    factory = RequestFactory()
    assert successful(factory.post("/login/", {"username": "blocked"})).status_code == 429
    assert successful(factory.post("/login/", {"username": "other"})).status_code == 200

    @module.throttle_failed_logins
    def broken(request):
        raise RuntimeError("synthetic failure")

    with pytest.raises(RuntimeError):
        broken(factory.post("/login/", {"username": "other"}))
    assert successful(factory.post("/login/", {"username": "other"})).status_code == 429
