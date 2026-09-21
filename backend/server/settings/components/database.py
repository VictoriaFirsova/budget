from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import os

from dotenv import load_dotenv

load_dotenv()
load_dotenv(dotenv_path=Path(".env"))


def _database_from_url(database_url: str) -> dict:
    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url[len("postgres://") :]

    parsed = urlparse(database_url)
    query = parse_qs(parsed.query)
    sslmode = (query.get("sslmode") or ["require"])[0]
    hostname = parsed.hostname or ""

    options = {}
    if "railway" in hostname or sslmode == "require":
        options["sslmode"] = sslmode or "require"

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote((parsed.path or "/").lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": hostname,
        "PORT": str(parsed.port or "5432"),
        "OPTIONS": options,
    }


database_url = os.getenv("DATABASE_URL")
if database_url:
    DATABASES = {"default": _database_from_url(database_url)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_NAME"),
            "USER": os.getenv("POSTGRES_USER"),
            "PASSWORD": os.getenv("POSTGRES_PASS"),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
