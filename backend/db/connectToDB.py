import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

def connectToDB():
    #load env variables from backend
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)
    password = os.getenv("DATABASE_PASSWORD")
    host = os.getenv("DATABASE_HOST")

    try:
        conn = psycopg2.connect(
            database="alarm_system",
            user="postgres",
            password=password,
            host=host,
            port="5432",
            connect_timeout=3,
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise Exception(f"Connection unsuccessful: {e}")
