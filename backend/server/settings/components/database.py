from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()
dotenv_path = Path(".env")
load_dotenv(dotenv_path=dotenv_path)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_NAME"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASS"),
        "HOST": "localhost",
        "PORT": "5432",
    }
}
