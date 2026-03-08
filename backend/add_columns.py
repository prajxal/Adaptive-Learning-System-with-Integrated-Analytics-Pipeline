import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import text
from db.database import engine

with engine.begin() as conn:
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR;"))
    except Exception as e:
        print(e)
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN google_connected BOOLEAN DEFAULT FALSE;"))
    except Exception as e:
        print(e)
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR;"))
    except Exception as e:
        print(e)
print("Migration completed")
