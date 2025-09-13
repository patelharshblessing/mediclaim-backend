# app/config.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # (Your existing settings like FILE_SIZE_LIMIT_MB)
    FILE_SIZE_LIMIT_MB: int = 5
    ALLOWED_MIMETYPES: list = ["application/pdf"]

    # --- NEW JWT SETTINGS ---
    # This secret key should be a long, random string in a real application
    # You can generate one using: openssl rand -hex 32
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10000

    OPENAI_API_KEY: str
    GEMINI_API_KEY: str  # <-- Change from OPENAI_API_KEY
    DATABASE_URL: str = (
        "postgresql://mediclaim_user:blessingsofttech@localhost/mediclaim_db"
    )

    class Config:
        env_file = ".env"  # Use .env for real secrets


settings = Settings()
