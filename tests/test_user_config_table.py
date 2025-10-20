import json
import sqlite3
import pytest
import time

@pytest.fixture
def db_connection():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    with open("./db/user_config.sql") as f:
        conn.executescript(f.read())
    yield conn
    conn.close()

def test_user_config_insert_and_query(db_connection):
    cursor = db_connection.cursor()

    # Insert a new config record
    cursor.execute("""
        INSERT INTO UserConfig (
            user_config_id,
            consent_given,
            use_external_services,
            external_services,
            default_ignore_patterns
        )     
        VALUES (?, ?, ?, ?, ?)""", 
        (1, True, False, json.dumps({"openai": True, "github_api": False}), json.dumps(["__pycache__", ".git"]))
    )
    db_connection.commit()

    # Verify correct insertion
    cursor.execute("SELECT * FROM UserConfig WHERE user_config_id = 1")
    row = cursor.fetchone()

    assert row is not None
    assert row[1] == 1
    assert row[2] == 0

    external_services = json.loads(row[3])
    default_ignore_patterns = json.loads(row[4])
    
    assert external_services == {"openai": True, "github_api": False}
    assert default_ignore_patterns == ["__pycache__", ".git"]

def test_user_config_update(db_connection):
    cursor = db_connection.cursor()

    # Insert initial config
    cursor.execute("INSERT INTO UserConfig (user_config_id, consent_given, use_external_services) VALUES (1, 0, 0)")

    # Update config
    cursor.execute("UPDATE UserConfig SET consent_given = ?, use_external_services = ? WHERE user_config_id = 1", (1, 1))
    db_connection.commit()

    # Check for updated values
    cursor.execute("SELECT consent_given, use_external_services FROM UserConfig WHERE user_config_id = 1")
    row = cursor.fetchone()
    assert row == (1, 1)

def test_timestamp_updates_on_change_trigger(db_connection):

    cursor = db_connection.cursor()

    # Insert initial config and get timestamp
    cursor.execute("INSERT INTO UserConfig (user_config_id, consent_given, use_external_services) VALUES (1, 0, 0)")
    cursor.execute("SELECT updated_at FROM UserConfig WHERE user_config_id = 1")
    old_timestamp = cursor.fetchone()[0]

    # Update config, have to sleep to force difference in timestamp
    time.sleep(1)
    cursor.execute("UPDATE UserConfig SET consent_given = ?, use_external_services = ? WHERE user_config_id = 1", (1, 1))
    db_connection.commit()

    # Test for updated timestamp
    cursor.execute("SELECT updated_at FROM UserConfig WHERE user_config_id = 1")
    new_timestamp = cursor.fetchone()[0]

    assert new_timestamp > old_timestamp