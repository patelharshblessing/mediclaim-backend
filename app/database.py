# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings
from .logger import get_logger

logger = get_logger(__name__)

# Create the SQLAlchemy engine
try:
    engine = create_engine(settings.DATABASE_URL)
    logger.info("Database engine created successfully.")
except Exception as e:
    logger.error("Error creating database engine: %s", e, exc_info=True)
    raise

# Each instance of SessionLocal will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our SQLAlchemy models to inherit from
Base = declarative_base()


# Dependency for API endpoints to get a DB session
def get_db():
    db = SessionLocal()
    try:
        logger.info("Database session started.")
        yield db
    except Exception as e:
        logger.error("Error during database session: %s", e, exc_info=True)
        raise
    finally:
        db.close()
        logger.info("Database session closed.")
