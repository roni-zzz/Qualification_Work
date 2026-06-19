import unittest
from unittest.mock import MagicMock, patch

import psycopg2

from db import addAvailableSystems
from db import connectMCtoAlarmSystem
from db import connectToAlarmSystem
from db import insertIntoDB


#test insertion into mock db
class TestCreateAlarmSystem(unittest.TestCase):
    #mock password generation
    @patch("db.addAvailableSystems.bcrypt.gensalt", return_value=b"salt")
    @patch("db.addAvailableSystems.bcrypt.hashpw", return_value=b"hashed_password")
    @patch("db.addAvailableSystems.generate_random_password", return_value="Pass12345678")
    def test_create_alarm_system_inserts_and_returns_id(
        self, _mock_password, _mock_hashpw, _mock_gensalt
    ):
        cursor = MagicMock()
        cursor.fetchone.return_value = [42]

        alarm_system_id, password = addAvailableSystems.create_alarm_system(cursor)

        self.assertEqual(alarm_system_id, 42)
        self.assertEqual(password, "Pass12345678")

        execute_args, execute_kwargs = cursor.execute.call_args
        self.assertIn("INSERT INTO alarm_system_table", execute_args[0])
        self.assertEqual(execute_args[1], ("hashed_password",))
        self.assertEqual(execute_kwargs, {})

#1 - test connection to microcontroller with normal variables
#2 - test connection to already connected microcontroller (should return false)
#3 - test connection to none alarm system (should return false)
class TestConnectMicroController(unittest.TestCase):

    
    @patch("db.connectMCtoAlarmSystem.connectToAlarmSystem.getCurrentAlarmSystemID", return_value=7)
    @patch("db.connectMCtoAlarmSystem.connectToDB.connectToDB")
    def test_connect_microcontroller_success(self, mock_connect_to_db, _mock_get_system_id):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        mock_connect_to_db.return_value = conn

        result = connectMCtoAlarmSystem.connectMicroController(1001, 1)

        self.assertTrue(result)
        cursor.execute.assert_called_once_with(
            """
            INSERT INTO microcontroller (microcontroller_id, alarm_system_id, current_state)
            VALUES (%s, %s, %s)
            ON CONFLICT (microcontroller_id) DO UPDATE SET
                alarm_system_id = EXCLUDED.alarm_system_id,
                current_state = EXCLUDED.current_state
            """,
            (1001, 7, "idle"),
        )
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()

    @patch("db.connectMCtoAlarmSystem.connectToAlarmSystem.getCurrentAlarmSystemID", return_value=7)
    @patch("db.connectMCtoAlarmSystem.connectToDB.connectToDB")
    def test_connect_microcontroller_rolls_back_on_insert_error(
        self, mock_connect_to_db, _mock_get_system_id
    ):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.execute.side_effect = Exception("insert failed")
        conn.cursor.return_value = cursor
        mock_connect_to_db.return_value = conn

        result = connectMCtoAlarmSystem.connectMicroController(1001, 1)

        self.assertFalse(result)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()

    @patch("db.connectMCtoAlarmSystem.connectToAlarmSystem.getCurrentAlarmSystemID", return_value=None)
    @patch("db.connectMCtoAlarmSystem.connectToDB.connectToDB")
    def test_connect_microcontroller_returns_false_when_user_unpaired(
        self, mock_connect_to_db, _mock_get_system_id
    ):
        conn = MagicMock()
        mock_connect_to_db.return_value = conn

        result = connectMCtoAlarmSystem.connectMicroController(1001, 1)

        self.assertFalse(result)
        conn.cursor.assert_not_called()
        conn.commit.assert_not_called()
        conn.rollback.assert_not_called()

#1 - test pairing of user to alarm system
#2 - test pairing to already paired system  
class TestConnectUserToSystem(unittest.TestCase):
    @patch("db.connectToAlarmSystem.bcrypt.checkpw", return_value=True)
    @patch("db.connectToAlarmSystem.connectToDB.connectToDB")
    def test_connect_user_to_system_pairs_when_password_matches(
        self, mock_connect_to_db, _mock_checkpw
    ):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = (None,)
        cursor.fetchall.return_value = [(11, "stored_hash")]
        mock_connect_to_db.return_value = conn

        result = connectToAlarmSystem.connectUserToSystem(1, "pw")

        self.assertTrue(result)
        self.assertEqual(cursor.execute.call_count, 4)
        cursor.execute.assert_any_call(
            "SELECT alarm_system_id FROM user_table WHERE id = %s",
            (1,),
        )
        cursor.execute.assert_any_call(
            """
            SELECT alarm_system_id, system_password_hash
            FROM alarm_system_table
            WHERE paired = FALSE
            """
        )
        cursor.execute.assert_any_call(
            """
            UPDATE user_table
            SET alarm_system_id = %s
            WHERE id = %s
            """,
            (11, 1),
        )
        cursor.execute.assert_any_call(
            "UPDATE alarm_system_table SET paired = TRUE WHERE alarm_system_id = %s",
            (11,),
        )
        conn.commit.assert_called_once()

    @patch("db.connectToAlarmSystem.connectToDB.connectToDB")
    def test_connect_user_to_system_returns_false_if_already_paired(
        self, mock_connect_to_db
    ):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = (3,)
        mock_connect_to_db.return_value = conn

        result = connectToAlarmSystem.connectUserToSystem(1, "pw")
        self.assertFalse(result)
        conn.commit.assert_not_called()

    @patch("db.connectToAlarmSystem.bcrypt.checkpw", return_value=False)
    @patch("db.connectToAlarmSystem.connectToDB.connectToDB")
    def test_connect_user_to_system_returns_false_if_password_does_not_match(
        self, mock_connect_to_db, _mock_checkpw
    ):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = (None,)
        cursor.fetchall.return_value = [(11, "stored_hash")]
        mock_connect_to_db.return_value = conn

        result = connectToAlarmSystem.connectUserToSystem(1, "wrong")
        self.assertFalse(result)
        conn.commit.assert_not_called()

#1 - test insertion of normal data in db
#2 - test insertion of duplicate username and alarm system id in db
class TestInsertUserInDB(unittest.TestCase):
    @patch("db.insertIntoDB.bcrypt.gensalt", return_value=b"salt")
    @patch("db.insertIntoDB.bcrypt.hashpw", return_value=b"hashed")
    @patch("db.insertIntoDB.connectToDB.connectToDB")
    def test_insert_user_commits_on_success(
        self, mock_connect_to_db, _mock_hashpw, _mock_gensalt
    ):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        mock_connect_to_db.return_value = conn

        result = insertIntoDB.insertUserInDB("alice", "alice@example.com", 5, "Secret123")

        self.assertTrue(result)
        cursor.execute.assert_called_once_with(
            """
            INSERT INTO user_table(username, email, alarm_system_id, password_hash, role)
            VALUES(%s, %s, %s, %s, %s)
            """,
            ("alice", "alice@example.com", 5, "hashed", "user"),
        )
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    @patch("db.insertIntoDB.bcrypt.gensalt", return_value=b"salt")
    @patch("db.insertIntoDB.bcrypt.hashpw", return_value=b"hashed")
    @patch("db.insertIntoDB.connectToDB.connectToDB")
    def test_insert_user_accepts_custom_role(
        self, mock_connect_to_db, _mock_hashpw, _mock_gensalt
    ):
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        mock_connect_to_db.return_value = conn

        result = insertIntoDB.insertUserInDB(
            "alice", "alice@example.com", 5, "Secret123", role="admin"
        )

        self.assertTrue(result)
        cursor.execute.assert_called_once_with(
            """
            INSERT INTO user_table(username, email, alarm_system_id, password_hash, role)
            VALUES(%s, %s, %s, %s, %s)
            """,
            ("alice", "alice@example.com", 5, "hashed", "admin"),
        )
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
        conn.close.assert_called_once()

    @patch("db.insertIntoDB.bcrypt.gensalt", return_value=b"salt")
    @patch("db.insertIntoDB.bcrypt.hashpw", return_value=b"hashed")
    @patch("db.insertIntoDB.connectToDB.connectToDB")
    def test_insert_user_rolls_back_and_returns_false_on_integrity_error(
        self, mock_connect_to_db, _mock_hashpw, _mock_gensalt
    ):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.execute.side_effect = psycopg2.IntegrityError("duplicate key")
        conn.cursor.return_value = cursor
        mock_connect_to_db.return_value = conn

        result = insertIntoDB.insertUserInDB("alice", "alice@example.com", 5, "Secret123")

        self.assertFalse(result)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()
