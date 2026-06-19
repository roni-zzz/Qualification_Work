import time
import unittest
from pydantic import ValidationError
from app.validate2 import ValidateData, receive_data, validateCount, received_count, app
from fastapi.testclient import TestClient

#tests:
#1 - test with normal values
#2 - test with incorrect device id 
#3 - test with invalid event type
#4 - test with zero count
#5 - test with negative count
#6 - test with timestamp that is too old
#7 - test with timestamp in da future
#8 - test for timestamp witihin allowed boundary
#9 - test with empty device id 
#10 - test with missing required field timestamp
#11 - test with missing event type
class TestClass_ValidateData(unittest.TestCase):
    
    def testWithNormalValues(self):
        now = int(time.time())

        data = ValidateData(
            device_id="esp32_123243",
            event_type="door_open",
            count=1,
            timestamp=now)

        #check if class assign values correctly
        self.assertEqual(data.device_id, "esp32_123243")
        self.assertEqual(data.event_type, "door_open")
        self.assertEqual(data.count, 1)
        self.assertEqual(data.timestamp, now)
        

    def testWithIncorrectDeviceId(self):
        now = int(time.time())

        with self.assertRaises(ValidationError):
            data = ValidateData(
                device_id="esp32_ahahahha", 
                event_type="door_open", 
                count= 1, 
                timestamp=now)

    def testWithInvalidEventType(self):
        now = int(time.time())

        with self.assertRaises(ValidationError):
            ValidateData(
                device_id="esp32_123243",
                event_type="window_open",  # invalid
                count=1,
                timestamp=now
            )
    def testWithZeroCount(self):
        now = int(time.time())

        with self.assertRaises(ValidationError):
            ValidateData(
                device_id="esp32_123243",
                event_type="door_open",
                count=0,
                timestamp=now
            )
    def testWithNegativeCount(self):
        now = int(time.time())

        with self.assertRaises(ValidationError):
            ValidateData(
                device_id="esp32_123243",
                event_type="door_open",
                count=-5,
                timestamp=now
            )

    def testWithOldTimestamp(self):
        old_time = int(time.time()) - 500  # > 180 seconds

        with self.assertRaises(ValidationError):
            ValidateData(
                device_id="esp32_123243",
                event_type="door_open",
                count=1,
                timestamp=old_time
            )

    def testWithFutureTimestamp(self):
        future_time = int(time.time()) + 500  # > 180 seconds

        with self.assertRaises(ValidationError):
            ValidateData(
                device_id="esp32_123243",
                event_type="door_open",
                count=1,
                timestamp=future_time
            )
    
    def testTimestampBoundaryAllowed(self):
        boundary_time = int(time.time()) - 180

        data = ValidateData(
            device_id="esp32_123243",
            event_type="door_open",
            count=1,
            timestamp=boundary_time
        )

        self.assertEqual(data.timestamp, boundary_time)
    
    def testWithEmptyDeviceId(self):
        now = int(time.time())

        with self.assertRaises(ValidationError):
            ValidateData(
                device_id="",
                event_type="door_open",
                count=1,
                timestamp=now
            )
    
    def testMissingFieldTimeStamp(self):
        now = int(time.time())

        with self.assertRaises(ValidationError):
            ValidateData(
                device_id="esp32_123243",
                event_type="door_open",
                count=1
                # missing timestamp
            )

    def testMissingFieldDeviceID(self):
        now = int(time.time())

        with self.assertRaises(ValidationError):
            ValidateData(
                #missing event 
                event_type="door_open",
                count=1,
                timestamp = now
            )
    

    def testMissingFieldEventType(self):
        now = int(time.time())

        with self.assertRaises(ValidationError):
            ValidateData(
                device_id="esp32_123243",
                #missing event type
                count=1,
                timestamp = now
            )


#tests:
#same as the one at the top, but through a fast api function
class TestClass_receiveData(unittest.TestCase):
    def setUp(self):
        received_count.clear()
        self.client = TestClient(app)


    def test_receive_data_valid(self):
        response = self.client.post("/data", json={
            "device_id": "esp32_123456",
            "event_type": "door_open",
            "count": 3,
            "timestamp": int(time.time())
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(received_count, [3])


    def test_receive_data_invalid_device_id(self):
        response = self.client.post("/data", json={
            "device_id": "bad_id",
            "event_type": "door_open",
            "count": 3,
            "timestamp": int(time.time())
        })

        self.assertEqual(response.status_code, 422)
        self.assertEqual(received_count, [])


    def test_receive_data_invalid_event_type(self):
        response = self.client.post("/data", json={
            "device_id": "esp32_123456",
            "event_type": "window_open",
            "count": 3,
            "timestamp": int(time.time())
        })

        self.assertEqual(response.status_code, 422)
        self.assertEqual(received_count, [])


    def test_receive_data_invalid_count(self):
        response = self.client.post("/data", json={
            "device_id": "esp32_123456",
            "event_type": "door_open",
            "count": 0,
            "timestamp": int(time.time())
        })

        self.assertEqual(response.status_code, 422)
        self.assertEqual(received_count, [])

    def test_receive_data_invalid_timestamp(self):
        response = self.client.post("/data", json={
            "device_id": "esp32_123456",
            "event_type": "door_open",
            "count": 3,
            "timestamp": int(time.time()) - 500
        })

        self.assertEqual(response.status_code, 422)
        self.assertEqual(received_count, [])


    def test_receive_data_multiple_valid_requests(self):
        for i in range(1, 4):
            self.client.post("/data", json={
                "device_id": "esp32_123456",
                "event_type": "door_open",
                "count": i,
                "timestamp": int(time.time())
            })

        self.assertEqual(received_count, [1, 2, 3]) 