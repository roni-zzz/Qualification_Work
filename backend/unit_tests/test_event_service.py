"""
Unit tests for event_service: is_duplicate and is_sequence_valid.
Each test clears module-level state in setUp to prevent cross-test pollution.
"""

import time
import unittest
from unittest.mock import patch

from app.services import event_service
from app.services.event_service import is_duplicate, is_sequence_valid


class TestIsDuplicate(unittest.TestCase):

    def setUp(self):
        # Reset module-level dedup store before every test
        event_service._seen_events.clear()

    # --- basic behaviour ---

    def test_first_event_not_duplicate(self):
        self.assertFalse(is_duplicate("esp32_1", 1))

    def test_same_event_immediately_is_duplicate(self):
        is_duplicate("esp32_1", 1)
        self.assertTrue(is_duplicate("esp32_1", 1))

    def test_different_count_not_duplicate(self):
        is_duplicate("esp32_1", 1)
        self.assertFalse(is_duplicate("esp32_1", 2))

    def test_different_device_not_duplicate(self):
        is_duplicate("esp32_1", 1)
        self.assertFalse(is_duplicate("esp32_2", 1))

    def test_same_count_different_devices_independent(self):
        is_duplicate("esp32_1", 5)
        is_duplicate("esp32_2", 5)
        self.assertTrue(is_duplicate("esp32_1", 5))
        self.assertTrue(is_duplicate("esp32_2", 5))

    # --- dedup window expiry ---

    def test_event_outside_window_not_duplicate(self):
        """An entry older than 180 s should be evicted and the event accepted."""
        old_time = time.time() - 181
        event_service._seen_events[("esp32_1", 1)] = old_time
        self.assertFalse(is_duplicate("esp32_1", 1))

    def test_event_at_window_boundary_is_duplicate(self):
        """An entry exactly at cutoff (ts == now - 180) is NOT evicted (strict < used)."""
        fixed_now = 1_000_000.0
        # ts == cutoff exactly — cleanup is `ts < cutoff`, so this entry survives
        event_service._seen_events[("esp32_1", 1)] = fixed_now - 180
        with patch("app.services.event_service.time.time", return_value=fixed_now):
            self.assertTrue(is_duplicate("esp32_1", 1))

    def test_expired_entries_cleaned_up(self):
        """Calling is_duplicate should lazily remove stale entries."""
        old = time.time() - 200
        event_service._seen_events[("esp32_old", 99)] = old
        is_duplicate("esp32_1", 1)  # trigger cleanup
        self.assertNotIn(("esp32_old", 99), event_service._seen_events)

    def test_fresh_entries_not_cleaned_up(self):
        """Recent entries must not be removed during lazy cleanup."""
        is_duplicate("esp32_1", 1)
        is_duplicate("esp32_2", 2)  # trigger cleanup pass
        self.assertIn(("esp32_1", 1), event_service._seen_events)

    # --- multiple rapid events ---

    def test_multiple_unique_events_all_accepted(self):
        for i in range(1, 6):
            self.assertFalse(is_duplicate("esp32_1", i))

    def test_replay_of_any_previous_count_detected(self):
        for i in range(1, 6):
            is_duplicate("esp32_1", i)
        for i in range(1, 6):
            self.assertTrue(is_duplicate("esp32_1", i))


# ---------------------------------------------------------------------------
# is_sequence_valid
# ---------------------------------------------------------------------------

class TestIsSequenceValid(unittest.TestCase):

    def setUp(self):
        event_service._last_counts.clear()

    # --- first event ---

    def test_first_event_any_count_accepted(self):
        self.assertTrue(is_sequence_valid("esp32_1", 1))

    def test_first_event_high_count_accepted(self):
        self.assertTrue(is_sequence_valid("esp32_1", 100))

    def test_first_event_stores_count(self):
        is_sequence_valid("esp32_1", 5)
        self.assertEqual(event_service._last_counts["esp32_1"], 5)

    # --- sequential events ---

    def test_sequential_increment_accepted(self):
        is_sequence_valid("esp32_1", 1)
        self.assertTrue(is_sequence_valid("esp32_1", 2))

    def test_sequential_chain_all_accepted(self):
        for i in range(1, 6):
            self.assertTrue(is_sequence_valid("esp32_1", i))

    def test_count_updated_after_valid_sequence(self):
        is_sequence_valid("esp32_1", 3)
        is_sequence_valid("esp32_1", 4)
        self.assertEqual(event_service._last_counts["esp32_1"], 4)

    # --- gaps / resets (ESP may skip counts if POST failed; reboots reset counter) ---

    def test_skipped_count_accepted(self):
        """Gaps are allowed (e.g. firmware incremented before a failed POST)."""
        is_sequence_valid("esp32_1", 1)
        self.assertTrue(is_sequence_valid("esp32_1", 3))  # skipped 2

    def test_repeated_count_handled(self):
        is_sequence_valid("esp32_1", 1)
        self.assertIsInstance(is_sequence_valid("esp32_1", 1), bool)

    def test_decremented_count_handled(self):
        is_sequence_valid("esp32_1", 5)
        self.assertIsInstance(is_sequence_valid("esp32_1", 4), bool)

    def test_count_updated_after_gap(self):
        """
        Forward jump updates high-water; duplicate detection is separate (is_duplicate).
        """
        is_sequence_valid("esp32_1", 1)
        is_sequence_valid("esp32_1", 5)
        self.assertEqual(event_service._last_counts["esp32_1"], 5)

    # --- device isolation ---

    def test_different_devices_tracked_independently(self):
        is_sequence_valid("esp32_1", 1)
        is_sequence_valid("esp32_2", 10)
        self.assertTrue(is_sequence_valid("esp32_1", 2))
        self.assertTrue(is_sequence_valid("esp32_2", 11))

    def test_large_jump_on_one_device_does_not_affect_another(self):
        is_sequence_valid("esp32_1", 1)
        is_sequence_valid("esp32_2", 1)
        is_sequence_valid("esp32_1", 99)
        # esp32_2 should still accept its correct next count
        self.assertTrue(is_sequence_valid("esp32_2", 2))
