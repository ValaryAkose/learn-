from dotenv import load_dotenv


from pydantic_settings import BaseSettings, SettingsConfigDict

from typing import Any
from pydantic import field_validator

load_dotenv()


class Settings(BaseSettings):
    database_url: str = "sqlite://"
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    gemini_api_key: str = ""
    environment: str = "development"
    debug: bool = False
    admin_email: str = ""
    admin_password: str = ""
    admin_display_name: str = ""
    admin_registration_key: str = ""
    allowed_origins: Any = ["*"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        if v is None:
            return ["*"]
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                return ["*"]
            if v_stripped.startswith("["):
                try:
                    import json

                    return json.loads(v_stripped)
                except Exception:
                    return [
                        o.strip()
                        for o in v_stripped.strip("[]").split(",")
                        if o.strip()
                    ]
            return [o.strip() for o in v_stripped.split(",")]
        return ["*"]

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
