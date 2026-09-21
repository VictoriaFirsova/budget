from split_settings.tools import optional, include
from os import environ

VENV = environ.get("DJANGO_VENV") or "development"

base_settings = [
    "components/common.py",
    "components/database.py",
    optional("environments/{0}.py".format(VENV)),
    optional("environments/local.py"),
]

include(*base_settings)
