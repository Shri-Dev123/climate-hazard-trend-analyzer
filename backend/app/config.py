from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_uri: str | None = Field(default=None, alias="MONGODB_URI")
    mongodb_db: str = Field(default="climate_hazard_analyzer", alias="MONGODB_DB")
    frontend_origins: str = Field(default="http://localhost:5173", alias="FRONTEND_ORIGINS")
    frontend_origin_regex: str | None = Field(default=None, alias="FRONTEND_ORIGIN_REGEX")
    open_meteo_archive_url: str = Field(
        default="https://archive-api.open-meteo.com/v1/archive",
        alias="OPEN_METEO_ARCHIVE_URL",
    )
    open_meteo_geocode_url: str = Field(
        default="https://geocoding-api.open-meteo.com/v1/search",
        alias="OPEN_METEO_GEOCODE_URL",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

