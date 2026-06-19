"""
Unit tests for input validation and sanitisation on request models.
Covers: CreateUserRequest, PairUserRequest, ConnectMicrocontrollerRequest
"""

import unittest
from pydantic import ValidationError

from app.models.request_models import (
    CreateUserRequest,
    PairUserRequest,
    ConnectMicrocontrollerRequest,
)


# ---------------------------------------------------------------------------
# CreateUserRequest
# ---------------------------------------------------------------------------

class TestCreateUserRequest(unittest.TestCase):

    def _valid(self, **overrides):
        data = {"username": "alice", "email": "alice@example.com", "password": "securepass1"}
        data.update(overrides)
        return CreateUserRequest(**data)

    # --- username ---

    def test_valid_username(self):
        req = self._valid(username="alice")
        self.assertEqual(req.username, "alice")

    def test_username_too_short_raises(self):
        with self.assertRaises(ValidationError):
            self._valid(username="a")  # 1 char, min is 2

    def test_username_exactly_min_length_allowed(self):
        req = self._valid(username="ab")
        self.assertEqual(req.username, "ab")

    def test_username_exactly_max_length_allowed(self):
        req = self._valid(username="a" * 50)
        self.assertEqual(len(req.username), 50)

    def test_username_too_long_raises(self):
        with self.assertRaises(ValidationError):
            self._valid(username="a" * 51)

    def test_username_missing_raises(self):
        with self.assertRaises(ValidationError):
            CreateUserRequest(email="a@b.com", password="securepass1")

    # --- email ---

    def test_valid_email(self):
        req = self._valid(email="user@domain.com")
        self.assertEqual(req.email, "user@domain.com")

    def test_invalid_email_no_at_raises(self):
        with self.assertRaises(ValidationError):
            self._valid(email="notanemail")

    def test_invalid_email_no_domain_raises(self):
        with self.assertRaises(ValidationError):
            self._valid(email="user@")

    def test_invalid_email_empty_raises(self):
        with self.assertRaises(ValidationError):
            self._valid(email="")

    def test_email_missing_raises(self):
        with self.assertRaises(ValidationError):
            CreateUserRequest(username="alice", password="securepass1")

    # --- password ---

    def test_valid_password(self):
        req = self._valid(password="strongpass")
        self.assertEqual(req.password, "strongpass")

    def test_password_too_short_raises(self):
        with self.assertRaises(ValidationError):
            self._valid(password="short")  # 5 chars, min is 8

    def test_password_exactly_min_length_allowed(self):
        req = self._valid(password="12345678")
        self.assertEqual(req.password, "12345678")

    def test_password_exactly_max_length_allowed(self):
        req = self._valid(password="a" * 128)
        self.assertEqual(len(req.password), 128)

    def test_password_too_long_raises(self):
        with self.assertRaises(ValidationError):
            self._valid(password="a" * 129)

    def test_password_missing_raises(self):
        with self.assertRaises(ValidationError):
            CreateUserRequest(username="alice", email="alice@example.com")


# ---------------------------------------------------------------------------
# PairUserRequest
# ---------------------------------------------------------------------------

class TestPairUserRequest(unittest.TestCase):

    def test_valid_request(self):
        req = PairUserRequest(system_password="mysecretpw")
        self.assertEqual(req.system_password, "mysecretpw")

    def test_system_password_too_short_raises(self):
        with self.assertRaises(ValidationError):
            PairUserRequest(system_password="short")  # 5 chars, min is 8

    def test_system_password_exactly_min_length_allowed(self):
        req = PairUserRequest(system_password="12345678")
        self.assertEqual(req.system_password, "12345678")

    def test_system_password_missing_raises(self):
        with self.assertRaises(ValidationError):
            PairUserRequest()

    def test_username_is_optional(self):
        req = PairUserRequest(system_password="mysecretpw")
        self.assertIsNone(req.username)

    def test_username_can_be_set(self):
        req = PairUserRequest(username="alice", system_password="mysecretpw")
        self.assertEqual(req.username, "alice")


# ---------------------------------------------------------------------------
# ConnectMicrocontrollerRequest
# ---------------------------------------------------------------------------

class TestConnectMicrocontrollerRequest(unittest.TestCase):

    def test_valid_request(self):
        req = ConnectMicrocontrollerRequest(microcontroller_id=1)
        self.assertEqual(req.microcontroller_id, 1)

    def test_zero_microcontroller_id_raises(self):
        with self.assertRaises(ValidationError):
            ConnectMicrocontrollerRequest(microcontroller_id=0)

    def test_negative_microcontroller_id_raises(self):
        with self.assertRaises(ValidationError):
            ConnectMicrocontrollerRequest(microcontroller_id=-5)

    def test_large_valid_id_accepted(self):
        req = ConnectMicrocontrollerRequest(microcontroller_id=999999)
        self.assertEqual(req.microcontroller_id, 999999)

    def test_microcontroller_id_missing_raises(self):
        with self.assertRaises(ValidationError):
            ConnectMicrocontrollerRequest()

    def test_username_is_optional(self):
        req = ConnectMicrocontrollerRequest(microcontroller_id=1)
        self.assertIsNone(req.username)

    def test_non_integer_id_raises(self):
        with self.assertRaises(ValidationError):
            ConnectMicrocontrollerRequest(microcontroller_id="abc")
