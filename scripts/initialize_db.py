# scripts/initialize_db.py

import os
import sys

# This adds the root project directory to the Python path
# so we can import from the 'app' module.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import engine
from app.database_schema import Base


def create_database_tables():
    """
    Connects to the database and creates all tables defined in app/models.py
    if they do not already exist.
    """
    print("Connecting to the database...")
    try:
        # The create_all command is idempotent, meaning it won't
        # try to re-create tables that already exist.
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully (if they didn't exist).")
    except Exception as e:
        print(f"❌ An error occurred while creating tables: {e}")


if __name__ == "__main__":
    create_database_tables()
