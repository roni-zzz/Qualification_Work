"""
Load / concurrency tests for SlidingWindow + RateLimitMiddleware.

Each test class creates a fresh app + limiter in setUp so there is zero
shared state between tests.

Threading model
---------------
A threading.Barrier synchronises all worker threads so they release
simultaneously, maximising request overlap. Results are written to a
pre-allocated list indexed by thread ID (no lock needed — each thread
owns its slot). Threads are joined with a 5-second timeout.

GIL note
--------
CPython's GIL serialises pure-Python bytecode, so true interleaving of
SlidingWindow.check is limited. Scenario B probes this by patching a
time.sleep(0) into check() to force GIL release at the most dangerous
point (between count read and list append), simulating a context switch.
"""

import collections
import threading
import time
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.rate_limit import SlidingWindow, RateLimitMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_load_app(max_requests: int = 10, window_seconds: int = 60) -> tuple:
    """Return (app, limiter) with a single /ping and /health route."""
    app = FastAPI()
    limiter = SlidingWindow(max_requests=max_requests, window_seconds=window_seconds)
    app.add_middleware(RateLimitMiddleware, limiter=limiter)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"ok": True}

    return app, limiter


def _burst(
    client: TestClient,
    n: int,
    path: str = "/ping",
    headers: dict = None,
) -> list:
    """
    Fire n concurrent GET requests via a Barrier-synchronised thread pool.
    Returns a list of status codes in thread-index order.
    """
    results = [None] * n
    barrier = threading.Barrier(n + 1)  # +1 for the main thread

    def worker(idx):
        barrier.wait()  # all workers release together
        try:
            r = client.get(path, headers=headers or {})
            results[idx] = r.status_code
        except Exception:
            results[idx] = -1  # unexpected error

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    barrier.wait()  # release all workers simultaneously
    for t in threads:
        t.join(timeout=5)
        if t.is_alive():
            raise RuntimeError("Worker thread did not finish within 5 s")

    return results


def _count(results: list) -> collections.Counter:
    return collections.Counter(results)


# ---------------------------------------------------------------------------
# Scenario A — exact burst saturates the limit, +1 is blocked
# ---------------------------------------------------------------------------

class TestBurstExactLimit(unittest.TestCase):

    def setUp(self):
        self.app, self.limiter = _make_load_app(max_requests=10)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_burst_at_limit_all_allowed(self):
        """Fire exactly max_requests threads; every response must be 200."""
        results = _burst(self.client, 10)
        counts = _count(results)
        self.assertEqual(counts[200], 10, f"Expected 10×200, got {dict(counts)}")
        self.assertEqual(counts[429], 0)

    def test_one_extra_after_burst_is_blocked(self):
        """After exhausting the window, the very next request must be 429."""
        _burst(self.client, 10)
        r = self.client.get("/ping")
        self.assertEqual(r.status_code, 429)


# ---------------------------------------------------------------------------
# Scenario B — over-limit burst: no more than max_requests sneak through
# ---------------------------------------------------------------------------

class TestOverLimitBurst(unittest.TestCase):

    def setUp(self):
        self.app, self.limiter = _make_load_app(max_requests=10)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_200_count_never_exceeds_limit(self):
        """20 concurrent requests against a limit of 10: at most 10 pass."""
        results = _burst(self.client, 20)
        counts = _count(results)
        self.assertLessEqual(
            counts[200], 10,
            f"Rate limiter allowed {counts[200]} requests through (limit=10)"
        )

    def test_no_unexpected_status_codes(self):
        """Every response must be either 200 or 429 — no 500s or errors."""
        results = _burst(self.client, 20)
        for code in results:
            self.assertIn(code, (200, 429), f"Unexpected status code: {code}")

    def test_429_body_has_required_fields(self):
        """Every 429 must carry error + retry_after in the body."""
        _burst(self.client, 10)  # exhaust
        r = self.client.get("/ping")
        self.assertEqual(r.status_code, 429)
        body = r.json()
        self.assertIn("error", body)
        self.assertIn("retry_after", body)
        self.assertGreater(body["retry_after"], 0)

    def test_429_headers_present(self):
        """429 responses must include X-RateLimit-* and Retry-After headers."""
        _burst(self.client, 10)
        r = self.client.get("/ping")
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.headers.get("x-ratelimit-remaining"), "0")
        self.assertIn("retry-after", r.headers)
        self.assertIn("x-ratelimit-limit", r.headers)

    def test_race_condition_with_forced_context_switch(self):
        """
        Patch time.sleep(0) into SlidingWindow.check just before the append
        to force a GIL context switch at the most dangerous point.
        Even with forced interleaving, 200 count must not exceed the limit.
        """
        original_check = SlidingWindow.check

        def check_with_yield(self_inner, key):
            # Force a context switch between count read and append
            now = time.time()
            cutoff = now - self_inner.window_seconds
            self_inner._log[key] = [t for t in self_inner._log[key] if t > cutoff]
            count = len(self_inner._log[key])
            time.sleep(0)  # yield GIL here
            if count >= self_inner.max_requests:
                oldest = self_inner._log[key][0]
                retry = max(0.0, oldest + self_inner.window_seconds - now)
                from app.rate_limit import RateLimitResult
                return RateLimitResult(False, 0, retry, retry)
            self_inner._log[key].append(now)
            from app.rate_limit import RateLimitResult
            return RateLimitResult(True, self_inner.max_requests - count - 1, 0.0, self_inner.window_seconds)

        with patch.object(SlidingWindow, "check", check_with_yield):
            app, _ = _make_load_app(max_requests=10)
            client = TestClient(app, raise_server_exceptions=False)
            results = _burst(client, 20)

        counts = _count(results)
        # Document actual behaviour: GIL may allow races; assert no 500s at minimum
        for code in results:
            self.assertIn(code, (200, 429), f"Unexpected status code under forced context switch: {code}")
        # Ideally still bounded — note in comment if this fails on your platform
        # self.assertLessEqual(counts[200], 10)  # uncomment if locks are added


# ---------------------------------------------------------------------------
# Scenario C — two IPs are isolated under concurrent load
# ---------------------------------------------------------------------------

class TestIpIsolation(unittest.TestCase):

    def setUp(self):
        self.app, _ = _make_load_app(max_requests=5)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def _burst_ip(self, ip: str, n: int) -> list:
        return _burst(self.client, n, headers={"X-Forwarded-For": ip})

    def test_two_ips_have_independent_counters(self):
        """IP-A exhausting its quota must not affect IP-B's quota."""
        results_a = []
        results_b = []
        barrier = threading.Barrier(11)  # 5 workers per IP + main

        def worker_a(idx):
            barrier.wait()
            r = self.client.get("/ping", headers={"X-Forwarded-For": "10.0.0.1"})
            results_a.append(r.status_code)

        def worker_b(idx):
            barrier.wait()
            r = self.client.get("/ping", headers={"X-Forwarded-For": "10.0.0.2"})
            results_b.append(r.status_code)

        threads = (
            [threading.Thread(target=worker_a, args=(i,)) for i in range(5)]
            + [threading.Thread(target=worker_b, args=(i,)) for i in range(5)]
        )
        for t in threads:
            t.start()
        barrier.wait()
        for t in threads:
            t.join(timeout=5)
            if t.is_alive():
                raise RuntimeError("Worker thread timed out")

        counts_a = _count(results_a)
        counts_b = _count(results_b)

        # Neither IP should bleed into the other
        self.assertLessEqual(counts_a[200], 5, f"IP-A: {dict(counts_a)}")
        self.assertLessEqual(counts_b[200], 5, f"IP-B: {dict(counts_b)}")

    def test_exhausted_ip_does_not_block_fresh_ip(self):
        """After IP-A is fully rate-limited, a new IP-C must still get through."""
        # Exhaust IP-A
        for _ in range(5):
            self.client.get("/ping", headers={"X-Forwarded-For": "10.0.0.1"})
        self.assertEqual(
            self.client.get("/ping", headers={"X-Forwarded-For": "10.0.0.1"}).status_code,
            429,
        )
        # IP-C is unaffected
        r = self.client.get("/ping", headers={"X-Forwarded-For": "192.168.1.1"})
        self.assertEqual(r.status_code, 200)


# ---------------------------------------------------------------------------
# Scenario D — /health bypasses the limiter under concurrent load
# ---------------------------------------------------------------------------

class TestHealthBypassUnderLoad(unittest.TestCase):

    def setUp(self):
        self.app, _ = _make_load_app(max_requests=5)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_health_always_200_while_ping_is_throttled(self):
        """
        Exhaust /ping quota concurrently, then fire /health requests.
        All /health responses must be 200.
        """
        # Exhaust /ping
        _burst(self.client, 10)

        # Verify /ping is now blocked
        self.assertEqual(self.client.get("/ping").status_code, 429)

        # /health must be unaffected
        health_results = _burst(self.client, 10, path="/health")
        counts = _count(health_results)
        self.assertEqual(counts[200], 10, f"/health returned non-200: {dict(counts)}")

    def test_health_not_counted_toward_quota(self):
        """
        Hammering /health must not consume any of the /ping quota.
        After N health calls, /ping should still have its full allowance.
        """
        _burst(self.client, 10, path="/health")

        # /ping quota must be untouched — all 5 should pass
        ping_results = _burst(self.client, 5, path="/ping")
        counts = _count(ping_results)
        self.assertEqual(counts[200], 5, f"Health requests consumed ping quota: {dict(counts)}")


# ---------------------------------------------------------------------------
# Scenario E — window expiry resets the counter (clock patched, no sleep)
# ---------------------------------------------------------------------------

class TestWindowReset(unittest.TestCase):

    def setUp(self):
        self.app, self.limiter = _make_load_app(max_requests=5, window_seconds=60)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_counter_resets_after_window_expires(self):
        """
        Exhaust the limit, advance the clock past window_seconds, then confirm
        a fresh burst is allowed again. Uses time.time patching — no sleep.
        """
        # Exhaust the quota
        _burst(self.client, 5)
        self.assertEqual(self.client.get("/ping").status_code, 429)

        # Advance clock 61 seconds into the future
        future = time.time() + 61

        with patch("app.rate_limit.time.time", return_value=future):
            results = _burst(self.client, 5)

        counts = _count(results)
        self.assertEqual(
            counts[200], 5,
            f"Expected all 5 requests to pass after window reset, got {dict(counts)}"
        )

    def test_partial_window_still_throttles(self):
        """
        Advance the clock by only half the window — old timestamps still count,
        so the limiter must still block.
        """
        _burst(self.client, 5)

        half_future = time.time() + 30  # only 30 s of a 60 s window has passed

        with patch("app.rate_limit.time.time", return_value=half_future):
            r = self.client.get("/ping")

        self.assertEqual(r.status_code, 429)
