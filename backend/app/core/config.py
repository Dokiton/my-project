from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Educational AI Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    @property
    def app_name(self) -> str:
        return self.PROJECT_NAME

    @property
    def environment(self) -> str:
        return self.ENVIRONMENT

    # Database (PostgreSQL)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "app_db"
    DATABASE_URL: str = ""

    @model_validator(mode="after")
    def build_database_url(self) -> "Settings":
        """Build DATABASE_URL from POSTGRES_* fields if not explicitly provided."""
        if not self.DATABASE_URL:
            user = quote_plus(self.POSTGRES_USER)
            password = quote_plus(self.POSTGRES_PASSWORD)
            self.DATABASE_URL = (
                f"postgresql+psycopg://{user}:{password}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @database_url.setter
    def database_url(self, value: str) -> None:
        self.DATABASE_URL = value

    # Keycloak (OIDC)
    KEYCLOAK_SERVER_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "edu-realm"
    KEYCLOAK_CLIENT_ID: str = "backend-client"
    KEYCLOAK_CLIENT_SECRET: str = "dummy_secret"

    # Ollama LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
