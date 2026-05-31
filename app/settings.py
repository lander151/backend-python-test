from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Notification Service"
    app_version: str = "1.0.0"
    debug: bool = False
    port: int = 5000

    # Provider
    provider_url: str = "http://provider:3001"
    provider_api_key: str = "test-dev-2026"
    provider_timeout: float = 10.0

    # Reintentos
    max_retries: int = 3
    retry_backoff: float = 1.0

    class Config:
        env_file = ".env"


settings = Settings()
