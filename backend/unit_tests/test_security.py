import time
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

import jwt
from fastapi.testclient import TestClient

from app.main import app

TEST_SECRET = "test-secret-that-is-long-enough-for-hs256"
TEST_USER_ID = 42
TEST_EMAIL = "test@example.com"


def make_token(
    secret=TEST_SECRET,
    user_id=TEST_USER_ID,
    email=TEST_EMAIL,
    exp_offset=3600,
    iat_offset=0,
    algorithm="HS256",
    omit_claims=None,
    extra_claims=None,
):
    """Build a JWT with sensible defaults; omit_claims removes required fields."""
    now = int(datetime.now(timezone.utc).timestamp())
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now + iat_offset,
        "exp": now + exp_offset,
    }
    if omit_claims:
        for claim in omit_claims:
            payload.pop(claim, None)
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret, algorithm=algorithm)


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class TestTokenOnEventsEndpoints(unittest.TestCase):
    """GET /events and GET /events/stream — auth-gated, no DB calls needed."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.settings_patch = patch("app.security.settings")
        self.mock_settings = self.settings_patch.start()
        self.mock_settings.jwt_secret = TEST_SECRET

    def tearDown(self):
        self.settings_patch.stop()

    # --- missing / malformed token ---

    def test_no_token_returns_401(self):
        response = self.client.get("/events")
        self.assertEqual(response.status_code, 401)

    def test_malformed_bearer_returns_401(self):
        response = self.client.get("/events", headers={"Authorization": "Bearer not.a.jwt"})
        self.assertEqual(response.status_code, 401)

    def test_wrong_scheme_returns_401(self):
        token = make_token()
        response = self.client.get("/events", headers={"Authorization": f"Basic {token}"})
        self.assertEqual(response.status_code, 401)

    # --- signature / secret issues ---

    def test_wrong_secret_returns_401(self):
        token = make_token(secret="wrong-secret")
        response = self.client.get("/events", headers=auth_header(token))
        self.assertEqual(response.status_code, 401)

    # --- expiry ---

    def test_expired_token_returns_401(self):
        token = make_token(exp_offset=-1)
        response = self.client.get("/events", headers=auth_header(token))
        self.assertEqual(response.status_code, 401)
        self.assertIn("expired", response.json()["detail"].lower())

    # --- missing required claims ---

    def test_missing_exp_returns_401(self):
        token = make_token(omit_claims=["exp"])
        response = self.client.get("/events", headers=auth_header(token))
        self.assertEqual(response.status_code, 401)

    def test_missing_iat_returns_401(self):
        token = make_token(omit_claims=["iat"])
        response = self.client.get("/events", headers=auth_header(token))
        self.assertEqual(response.status_code, 401)

    def test_missing_sub_returns_401(self):
        token = make_token(omit_claims=["sub"])
        response = self.client.get("/events", headers=auth_header(token))
        self.assertEqual(response.status_code, 401)

    def test_missing_email_claim_returns_401(self):
        token = make_token(omit_claims=["email"])
        # 'email' is not a JWT-required claim but get_current_user reads it
        response = self.client.get("/events", headers=auth_header(token))
        self.assertEqual(response.status_code, 401)
        self.assertIn("payload", response.json()["detail"].lower())

    # --- payload type issues ---

    def test_non_numeric_sub_returns_401(self):
        token = make_token(extra_claims={"sub": "not-a-number"})
        response = self.client.get("/events", headers=auth_header(token))
        self.assertEqual(response.status_code, 401)

    # --- future iat (clock-skew abuse) ---

    def test_iat_far_in_future_returns_401(self):
        # PyJWT raises ImmatureSignatureError (subclass of InvalidTokenError)
        # before security.py's custom iat check, so detail is "Invalid token"
        token = make_token(iat_offset=120)  # 120 s in the future
        response = self.client.get("/events", headers=auth_header(token))
        self.assertEqual(response.status_code, 401)

    @patch("db.connectToAlarmSystem.get_alarm_system_id_by_user_id", return_value=None)
    @patch("app.routers.events.get_alarm_system_id_for_user", return_value=None)
    def test_iat_at_current_time_returns_200(self, _mock_system_id, _mock_direct_db):
        """iat set to now (no skew) — should pass."""
        token = make_token(iat_offset=0)
        response = self.client.get("/events", headers=auth_header(token))
        self.assertEqual(response.status_code, 200)

    # --- valid token ---

    @patch("db.connectToAlarmSystem.get_alarm_system_id_by_user_id", return_value=None)
    @patch("app.routers.events.get_alarm_system_id_for_user", return_value=None)
    def test_valid_token_get_events_returns_200(self, _mock_system_id, _mock_direct_db):
        token = make_token()
        response = self.client.get("/events", headers=auth_header(token))
        self.assertEqual(response.status_code, 200)

    # --- unconfigured JWT secret ---

    def test_missing_jwt_secret_returns_500(self):
        self.mock_settings.jwt_secret = None
        token = make_token()
        response = self.client.get("/events", headers=auth_header(token))
        self.assertEqual(response.status_code, 500)


class TestTokenOnPairingEndpoints(unittest.TestCase):
    """POST /api/pair and POST /api/microcontroller/connect."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.settings_patch = patch("app.security.settings")
        self.mock_settings = self.settings_patch.start()
        self.mock_settings.jwt_secret = TEST_SECRET

    def tearDown(self):
        self.settings_patch.stop()

    def test_pair_no_token_returns_401(self):
        response = self.client.post("/api/pair", json={"system_password": "pass"})
        self.assertEqual(response.status_code, 401)

    def test_pair_expired_token_returns_401(self):
        token = make_token(exp_offset=-1)
        response = self.client.post(
            "/api/pair",
            json={"system_password": "pass"},
            headers=auth_header(token),
        )
        self.assertEqual(response.status_code, 401)

    def test_pair_wrong_secret_returns_401(self):
        token = make_token(secret="wrong")
        response = self.client.post(
            "/api/pair",
            json={"system_password": "pass"},
            headers=auth_header(token),
        )
        self.assertEqual(response.status_code, 401)

    def test_microcontroller_connect_no_token_returns_401(self):
        response = self.client.post(
            "/api/microcontroller/connect",
            json={"microcontroller_id": 1},
        )
        self.assertEqual(response.status_code, 401)

    def test_microcontroller_connect_expired_token_returns_401(self):
        token = make_token(exp_offset=-1)
        response = self.client.post(
            "/api/microcontroller/connect",
            json={"microcontroller_id": 1},
            headers=auth_header(token),
        )
        self.assertEqual(response.status_code, 401)


class TestTokenOnEventsPostEndpoint(unittest.TestCase):
    """POST /api/events — auth + device ownership check."""

    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.settings_patch = patch("app.security.settings")
        self.mock_settings = self.settings_patch.start()
        self.mock_settings.jwt_secret = TEST_SECRET

    def tearDown(self):
        self.settings_patch.stop()

    def _valid_payload(self):
        return {
            "device_id": "esp32_1",
            "event_type": "door_open",
            "count": 1,
            "timestamp": int(time.time()),
        }

    def test_no_token_returns_401(self):
        response = self.client.post("/api/events", json=self._valid_payload())
        self.assertEqual(response.status_code, 401)

    def test_expired_token_returns_401(self):
        token = make_token(exp_offset=-1)
        response = self.client.post(
            "/api/events", json=self._valid_payload(), headers=auth_header(token)
        )
        self.assertEqual(response.status_code, 401)

    def test_wrong_secret_returns_401(self):
        token = make_token(secret="bad")
        response = self.client.post(
            "/api/events", json=self._valid_payload(), headers=auth_header(token)
        )
        self.assertEqual(response.status_code, 401)

    @patch("app.routers.events.is_microcontroller_registered_to_user", return_value=False)
    def test_valid_token_unregistered_device_returns_403(self, _mock):
        token = make_token()
        response = self.client.post(
            "/api/events", json=self._valid_payload(), headers=auth_header(token)
        )
        self.assertEqual(response.status_code, 403)

    @patch("app.routers.events.is_microcontroller_registered_to_user", return_value=True)
    @patch("app.routers.events.is_duplicate", return_value=False)
    @patch("app.routers.events.is_sequence_valid", return_value=True)
    @patch("app.routers.events.get_alarm_system_id_for_device", return_value=None)
    def test_valid_token_registered_device_returns_200(self, _mock_alarm_id, _seq, _dup, _reg):
        token = make_token()
        response = self.client.post(
            "/api/events", json=self._valid_payload(), headers=auth_header(token)
        )
        self.assertEqual(response.status_code, 200)
