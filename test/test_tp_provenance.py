"""La contenerización no incorpora las ampliaciones funcionales del parcial."""
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "54c7fa2e362904999e07857636bb97f087877341"


@pytest.mark.parametrize("paths", [("app", "migrations"), ("requirements.txt", "alembic.ini", "seed.py")])
def test_original_tp_runtime_files_are_unchanged(paths):
    files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", SOURCE, "--", *paths], cwd=ROOT,
    ).decode().splitlines()
    assert files
    for relative in files:
        original = subprocess.check_output(["git", "show", f"{SOURCE}:{relative}"], cwd=ROOT)
        copied = (ROOT / "despliegue" / relative).read_bytes()
        assert copied.replace(b"\r\n", b"\n") == original.replace(b"\r\n", b"\n"), relative
