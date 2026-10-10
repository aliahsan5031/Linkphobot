"""Guards for problems found in the audit: leaked keys and the misnamed ignore file."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
KEY_PATTERN = re.compile(r"gsk_[A-Za-z0-9]{20,}")


def test_gitignore_has_the_leading_dot():
    assert (ROOT / ".gitignore").is_file()
    assert not (ROOT / "gitignore").exists()
    text = (ROOT / ".gitignore").read_text()
    assert ".env" in text and "*.key" in text
    assert "!.env.example" in text  # .env.* must not swallow the example file


def test_license_file_exists_for_the_declared_mit_license():
    assert "MIT License" in (ROOT / "LICENSE").read_text()


@pytest.mark.parametrize(
    "path",
    [p for p in ROOT.rglob("*") if p.suffix in {".py", ".md", ".txt", ".yml", ".toml"}
     and ".git" not in p.parts and ".pytest_cache" not in p.parts],
    ids=lambda p: str(p.relative_to(ROOT)),
)
def test_no_groq_key_is_committed(path):
    assert not KEY_PATTERN.search(path.read_text(errors="ignore")), f"key-like string in {path}"


def test_app_does_not_hardcode_a_key():
    source = (ROOT / "app.py").read_text()
    assert "GROQ_API_KEY =" not in source
    assert "key[:8]" not in source  # the old startup log leaked the key prefix
