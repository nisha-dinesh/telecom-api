# app/core/config.py
# Job of this file: read settings (database address, secret key...) from the .env file.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All app settings in one place. Each variable is read from .env by name."""

    # If DATABASE_URL is not found in .env, use this local SQLite file.
    DATABASE_URL: str = "sqlite:///./telecom.db"

    # NO default on purpose: if SECRET_KEY is missing from .env the app refuses
    # to start, instead of silently running with a guessable key (OWASP risk).
    SECRET_KEY: str

    # HS256 = the signing method used for our JWT tokens.
    ALGORITHM: str = "HS256"

    # How long a login token stays valid. Short = safer if a token leaks.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Browser origins allowed to call the API (comma separated).
    CORS_ORIGINS: str = "http://localhost:3000"

    # Tell pydantic-settings: "also read values from a file called .env"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# ONE Settings object, imported everywhere else.
settings = Settings()