from split_settings.tools import optional, include
from os import environ

VENV = environ.get("DJANGO_VENV") or "development"

base_settings = [
    "components/common.py",  # standard django settings
    "components/database.py",  # postgres
    # You can even use glob:
    # 'components/*.py'
    # Select the right env:
    "environments/{0}.py".format(VENV),
    # Optionally override some settings:
    optional("environments/local.py"),
]

# Include settings:
include(*base_settings)
