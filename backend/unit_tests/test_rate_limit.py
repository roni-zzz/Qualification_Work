import time
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.rate_limit import SlidingWindow, RateLimitMiddleware


# ---------------------------------------------------------------------------
# Minimal app used for middleware integration tests
# ---------------------------------------------------------------------------

def _make_app(max_requests: int, window_seconds: int) -> FastAPI:
    app = FastAPI()
    limiter = SlidingWindow(max_requests=max_requests, window_seconds=window_seconds)
    app.add_middleware(RateLimitMiddleware, limiter=limiter)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


# ---------------------------------------------------------------------------
# Unit tests: SlidingWindow
# ---------------------------------------------------------------------------

class TestSlidingWindow(unittest.TestCase):

    def test_first_request_is_allowed(self):
        limiter = SlidingWindow(max_requests=5, window_seconds=60)
        result = limiter.check("client1")
        self.assertTrue(result.allowed)

    def test_remaining_decrements(self):
        limiter = SlidingWindow(max_requests=5, window_seconds=60)
        r1 = limiter.check("client1")
        r2 = limiter.check("client1")
        self.assertEqual(r1.remaining, 4)
        self.assertEqual(r2.remaining, 3)

    def test_request_blocked_at_limit(self):
        limiter = SlidingWindow(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.check("client1")
        result = limiter.check("client1")
        self.assertFalse(result.allowed)
        self.assertEqual(result.remaining, 0)

    def test_retry_after_is_positive_when_blocked(self):
        limiter = SlidingWindow(max_requests=2, window_seconds=60)
        limiter.check("client1")
        limiter.check("client1")
        result = limiter.check("client1")
        self.assertFalse(result.allowed)
        self.assertGreater(result.retry_after, 0)

    def test_different_keys_tracked_independently(self):
        limiter = SlidingWindow(max_requests=2, window_seconds=60)
        limiter.check("a")
        limiter.check("a")
        # "a" is now at limit; "b" should still be allowed
        self.assertFalse(limiter.check("a").allowed)
        self.assertTrue(limiter.check("b").allowed)

    def test_old_timestamps_evicted_after_window(self):
        limiter = SlidingWindow(max_requests=2, window_seconds=1)
        now = time.time()
        # Manually inject two timestamps that are already outside the window
        limiter._log["client1"] = [now - 2, now - 2]
        result = limiter.check("client1")
        self.assertTrue(result.allowed)

    def test_reset_after_equals_window_when_allowed(self):
        limiter = SlidingWindow(max_requests=5, window_seconds=30)
        result = limiter.check("client1")
        self.assertEqual(result.reset_after, 30)


# ---------------------------------------------------------------------------
# Integration tests: RateLimitMiddleware via TestClient
# ---------------------------------------------------------------------------

class TestRateLimitMiddleware(unittest.TestCase):

    def setUp(self):
        self.app = _make_app(max_requests=3, window_seconds=60)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_requests_within_limit_return_200(self):
        for _ in range(3):
            response = self.client.get("/ping")
            self.assertEqual(response.status_code, 200)

    def test_request_over_limit_returns_429(self):
        for _ in range(3):
            self.client.get("/ping")
        response = self.client.get("/ping")
        self.assertEqual(response.status_code, 429)

    def test_429_response_contains_retry_after(self):
        for _ in range(3):
            self.client.get("/ping")
        response = self.client.get("/ping")
        body = response.json()
        self.assertIn("retry_after", body)
        self.assertGreater(body["retry_after"], 0)

    def test_429_response_contains_error_field(self):
        for _ in range(3):
            self.client.get("/ping")
        response = self.client.get("/ping")
        self.assertIn("error", response.json())

    # --- headers on allowed responses ---

    def test_ratelimit_limit_header_present(self):
        response = self.client.get("/ping")
        self.assertIn("x-ratelimit-limit", response.headers)
        self.assertEqual(response.headers["x-ratelimit-limit"], "3")

    def test_ratelimit_remaining_header_decrements(self):
        r1 = self.client.get("/ping")
        r2 = self.client.get("/ping")
        self.assertEqual(r1.headers["x-ratelimit-remaining"], "2")
        self.assertEqual(r2.headers["x-ratelimit-remaining"], "1")

    def test_ratelimit_reset_header_present(self):
        response = self.client.get("/ping")
        self.assertIn("x-ratelimit-reset", response.headers)

    # --- headers on 429 responses ---

    def test_429_includes_ratelimit_headers(self):
        for _ in range(3):
            self.client.get("/ping")
        response = self.client.get("/ping")
        self.assertEqual(response.headers["x-ratelimit-remaining"], "0")
        self.assertIn("retry-after", response.headers)

    # --- health endpoint bypass ---

    def test_health_endpoint_not_rate_limited(self):
        # exhaust the limit on /ping
        for _ in range(3):
            self.client.get("/ping")
        # /health should still return 200 regardless
        for _ in range(5):
            response = self.client.get("/health")
            self.assertEqual(response.status_code, 200)

    # --- X-Forwarded-For key extraction ---

    def test_forwarded_for_header_used_as_key(self):
        """Two IPs via X-Forwarded-For should have independent counters."""
        app = _make_app(max_requests=2, window_seconds=60)
        client = TestClient(app, raise_server_exceptions=False)

        # Exhaust limit for ip-a
        client.get("/ping", headers={"X-Forwarded-For": "10.0.0.1"})
        client.get("/ping", headers={"X-Forwarded-For": "10.0.0.1"})
        blocked = client.get("/ping", headers={"X-Forwarded-For": "10.0.0.1"})
        self.assertEqual(blocked.status_code, 429)

        # ip-b should still be allowed
        allowed = client.get("/ping", headers={"X-Forwarded-For": "10.0.0.2"})
        self.assertEqual(allowed.status_code, 200)

    def test_first_ip_used_from_forwarded_for_chain(self):
        """Only the first IP in a comma-separated X-Forwarded-For counts."""
        app = _make_app(max_requests=2, window_seconds=60)
        client = TestClient(app, raise_server_exceptions=False)

        client.get("/ping", headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"})
        client.get("/ping", headers={"X-Forwarded-For": "1.2.3.4, 9.9.9.9"})
        blocked = client.get("/ping", headers={"X-Forwarded-For": "1.2.3.4, 0.0.0.0"})
        self.assertEqual(blocked.status_code, 429)

        # Different first IP is unaffected
        allowed = client.get("/ping", headers={"X-Forwarded-For": "9.9.9.9"})
        self.assertEqual(allowed.status_code, 200)
