# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings

# Create the SQLAlchemy engine
engine = create_engine(settings.DATABASE_URL)

# Each instance of SessionLocal will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our SQLAlchemy models to inherit from
Base = declarative_base()


# Dependency for API endpoints to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
