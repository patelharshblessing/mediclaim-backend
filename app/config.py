# app/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # (Your existing settings like FILE_SIZE_LIMIT_MB)
    FILE_SIZE_LIMIT_MB: int = 5
    ALLOWED_MIMETYPES: list = ["application/pdf"]
    
    # --- NEW JWT SETTINGS ---
    # This secret key should be a long, random string in a real application
    # You can generate one using: openssl rand -hex 32
    JWT_SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    OPENAI_API_KEY: str
    DATABASE_URL: str = "postgresql://mediclaim_user:blessingsofttech@localhost/mediclaim_db"

    class Config:
        env_file = ".env" # Use .env for real secrets

settings = Settings()


#hello