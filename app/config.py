from __future__ import annotations



import os

from functools import lru_cache



from dotenv import load_dotenv

from pydantic import BaseModel, Field





class Settings(BaseModel):

    db_name: str = Field(default="marketplace-ai")

    db_user: str = Field(default="postgres")

    db_password: str = Field(default="")

    db_host: str = Field(default="localhost")

    db_port: int = Field(default=5432, ge=1, le=65535)

    ollama_model: str = Field(default="qwen2.5:7b-instruct")

    ollama_timeout_sec: float = Field(default=120.0, gt=0)





def _parse_int_env(name: str, default: str) -> int:

    raw = os.environ.get(name, default)

    try:

        return int(raw)

    except ValueError as exc:

        raise ValueError(f"Invalid {name}: {raw!r}") from exc





def _parse_float_env(name: str, default: str) -> float:

    raw = os.environ.get(name, default)

    try:

        return float(raw)

    except ValueError as exc:

        raise ValueError(f"Invalid {name}: {raw!r}") from exc





@lru_cache(maxsize=1)

def get_settings() -> Settings:

    load_dotenv()

    return Settings(

        db_name=os.environ.get("DB_NAME", "marketplace-ai"),

        db_user=os.environ.get("DB_USER", "postgres"),

        db_password=os.environ.get("DB_PASSWORD", ""),

        db_host=os.environ.get("DB_HOST", "localhost"),

        db_port=_parse_int_env("DB_PORT", "5432"),

        ollama_model=os.environ.get("OLLAMA_MODEL", "qwen2.5:7b-instruct"),

        ollama_timeout_sec=_parse_float_env("OLLAMA_TIMEOUT_SEC", "120"),

    )

