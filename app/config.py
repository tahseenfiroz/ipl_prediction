from __future__ import annotations

import os
from pathlib import Path


DEFAULT_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def load_gemini_api_key(explicit_api_key: str | None = None) -> str | None:
    if explicit_api_key:
        return explicit_api_key

    _load_dotenv(DEFAULT_ENV_PATH)

    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        return env_key

    return None


def load_rapidapi_config() -> tuple[str | None, str | None]:
    _load_dotenv(DEFAULT_ENV_PATH)
    api_key = os.getenv("RAPIDAPI_KEY") or os.getenv("X-RapidAPI-Key")
    api_host = os.getenv("RAPIDAPI_HOST") or os.getenv("X-RapidAPI-Host")
    return api_key, api_host


def _load_dotenv(env_path: Path) -> None:
    if not env_path.exists():
        return

    with open(env_path, encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
