import io
import json
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

from scripts import send_test_events

#1 - test with correct values
#2 - test with simulated 422 error(HTTP error)
#3 - simulate runtime error
class TestSendEvent(unittest.TestCase):
    #this sets current time to x, by assigning time.time = 170000000000.0
    @patch("scripts.send_test_events.time.time", return_value=1700000000.0)
    #take mock url
    @patch("scripts.send_test_events.urllib.request.urlopen")
    def test_send_event_success_posts_expected_payload(self, mock_urlopen, _mock_time):
        response = MagicMock()
        response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = response

        ok = send_test_events.send_event(
            "http://127.0.0.1:5000/", "esp32_001", "door_open", 7
        )

        self.assertTrue(ok)
        self.assertEqual(mock_urlopen.call_count, 1)

        req = mock_urlopen.call_args.args[0]
        timeout = mock_urlopen.call_args.kwargs["timeout"]
        payload = json.loads(req.data.decode("utf-8"))

        self.assertEqual(req.full_url, "http://127.0.0.1:5000/api/events")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Content-type"), "application/json")
        self.assertEqual(timeout, 5)
        self.assertEqual(
            payload,
            {
                "device_id": "esp32_001",
                "event_type": "door_open",
                "count": 7,
                "timestamp": 1700000000.0,
            },
        )

    @patch("scripts.send_test_events.urllib.request.urlopen")
    def test_send_event_returns_false_for_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="http://127.0.0.1:5000/api/events",
            code=422,
            msg="Unprocessable Entity",
            hdrs=None,
            fp=io.BytesIO(b'{"detail":"bad payload"}'),
        )

        ok = send_test_events.send_event(
            "http://127.0.0.1:5000", "esp32_001", "door_open", 1
        )
        self.assertFalse(ok)


    @patch("scripts.send_test_events.urllib.request.urlopen")
    def test_send_event_returns_false_for_generic_exception(self, mock_urlopen):
        mock_urlopen.side_effect = RuntimeError("network down")

        ok = send_test_events.send_event(
            "http://127.0.0.1:5000", "esp32_001", "door_open", 1
        )
        self.assertFalse(ok)

#1 - test that when method runs with --once, it sends exactly one event
#2 -  verify that main behaves correctly in sequence mode
class TestMain(unittest.TestCase):
    #mock event sent to be true
    @patch("scripts.send_test_events.send_event", return_value=True)
    #prevent waiting and ensure method  doesnt enter a loop
    @patch("scripts.send_test_events.time.sleep")
    #mock command line arguments
    @patch("scripts.send_test_events.argparse.ArgumentParser.parse_args")
    def test_main_once_mode_sends_single_event(
        self, mock_parse_args, mock_sleep, mock_send_event
    ):
        mock_parse_args.return_value = type(
            "Args",
            (),
            {"base": "http://localhost:5000/", "device": "esp32_123", "once": True, "both": False},
        )()

        send_test_events.main()

        mock_send_event.assert_called_once_with(
            "http://localhost:5000", "esp32_123", "door_open", 1
        )
        mock_sleep.assert_not_called()

    @patch("scripts.send_test_events.send_event", return_value=True)
    @patch("scripts.send_test_events.time.sleep")
    @patch("scripts.send_test_events.argparse.ArgumentParser.parse_args")
    def test_main_sequence_mode_sends_expected_events(
        self, mock_parse_args, mock_sleep, mock_send_event
    ):
        mock_parse_args.return_value = type(
            "Args",
            (),
            {"base": "http://localhost:5000/", "device": "esp32_456", "once": False, "both": False},
        )()

        send_test_events.main()

        self.assertEqual(
            mock_send_event.call_args_list,
            [
                unittest.mock.call(
                    "http://localhost:5000", "esp32_456", "door_open", 1
                ),
                unittest.mock.call(
                    "http://localhost:5000", "esp32_456", "door_closed", 2
                ),
                unittest.mock.call(
                    "http://localhost:5000", "esp32_456", "door_open", 3
                ),
                unittest.mock.call(
                    "http://localhost:5000", "esp32_456", "door_closed", 4
                ),
            ],
        )
        self.assertEqual(mock_sleep.call_count, 2)