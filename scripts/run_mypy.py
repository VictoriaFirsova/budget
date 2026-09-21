#!/usr/bin/env python3
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")

env = os.environ.copy()
env["PYTHONPATH"] = BACKEND

subprocess.check_call(
    [
        sys.executable,
        "-m",
        "mypy",
        f"--config-file={os.path.join(ROOT, 'mypy.ini')}",
        "--explicit-package-bases",
        "apps",
        "server",
    ],
    cwd=BACKEND,
    env=env,
)
