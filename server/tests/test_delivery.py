from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_is_present_and_non_root():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:" in dockerfile
    assert re.search(r"^USER\s+(?!root\b)\S+", dockerfile, re.MULTILINE)
    assert "python -m hbbs" in dockerfile
    assert "pip install" not in dockerfile
    assert "docker push" not in dockerfile.lower()


def test_readme_documents_environment_only_network_config():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "HBBS_BIND_HOST" in readme
    assert "HBBS_TLS_CERT" in readme
    assert "application/json" in readme
    assert "HBBS/1" in readme


def test_no_obvious_secret_defaults_in_source():
    for path in (ROOT / "hbbs").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "BEGIN PRIVATE KEY" not in text
        assert "correct horse" not in text
