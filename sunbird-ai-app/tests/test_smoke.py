"""
Smoke tests for the sunbird-ai-app project.

Verifies:
  - sunbird-ai-app/.env.example exists and contains SUNBIRD_API_TOKEN
  - Root .gitignore contains .env and *.env patterns
  - sunbird-ai-app/requirements.txt has pinned versions (every package line uses ==)
  - SunbirdClient raises ConfigurationError when SUNBIRD_API_TOKEN is absent
"""

from __future__ import annotations

import os
import sys

import pytest

# ---------------------------------------------------------------------------
# Path helpers — all paths are resolved relative to this test file so that
# the tests work regardless of where pytest is invoked from.
# ---------------------------------------------------------------------------

# sunbird-ai-app/tests/test_smoke.py  →  sunbird-ai-app/
_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_TESTS_DIR)          # sunbird-ai-app/
_REPO_ROOT = os.path.dirname(_APP_DIR)           # repository root

_ENV_EXAMPLE = os.path.join(_APP_DIR, ".env.example")
_REQUIREMENTS = os.path.join(_APP_DIR, "requirements.txt")
_GITIGNORE = os.path.join(_REPO_ROOT, ".gitignore")

# Ensure the app package is importable.
sys.path.insert(0, _APP_DIR)


# ---------------------------------------------------------------------------
# .env.example
# ---------------------------------------------------------------------------


class TestEnvExample:
    def test_env_example_exists(self) -> None:
        """sunbird-ai-app/.env.example must be present in the repository."""
        assert os.path.isfile(_ENV_EXAMPLE), (
            f".env.example not found at {_ENV_EXAMPLE}"
        )

    def test_env_example_contains_sunbird_api_token(self) -> None:
        """The .env.example file must declare the SUNBIRD_API_TOKEN variable."""
        with open(_ENV_EXAMPLE, encoding="utf-8") as fh:
            content = fh.read()
        assert "SUNBIRD_API_TOKEN" in content, (
            ".env.example does not contain SUNBIRD_API_TOKEN"
        )


# ---------------------------------------------------------------------------
# .gitignore
# ---------------------------------------------------------------------------


class TestGitignore:
    def test_gitignore_exists(self) -> None:
        """Root .gitignore must exist."""
        assert os.path.isfile(_GITIGNORE), (
            f".gitignore not found at {_GITIGNORE}"
        )

    def _gitignore_lines(self) -> list[str]:
        with open(_GITIGNORE, encoding="utf-8") as fh:
            return [line.strip() for line in fh.readlines()]

    def test_gitignore_contains_dotenv(self) -> None:
        """Root .gitignore must contain a '.env' pattern to protect secrets."""
        lines = self._gitignore_lines()
        assert ".env" in lines, (
            ".gitignore does not contain a '.env' entry"
        )

    def test_gitignore_contains_star_dotenv(self) -> None:
        """Root .gitignore must contain a '*.env' pattern."""
        lines = self._gitignore_lines()
        assert "*.env" in lines, (
            ".gitignore does not contain a '*.env' entry"
        )


# ---------------------------------------------------------------------------
# requirements.txt — pinned versions
# ---------------------------------------------------------------------------


def _is_comment_or_blank(line: str) -> bool:
    stripped = line.strip()
    return stripped == "" or stripped.startswith("#")


class TestRequirementsPinned:
    def test_all_packages_have_pinned_versions(self) -> None:
        """Every non-comment, non-blank line in requirements.txt must use '=='."""
        with open(_REQUIREMENTS, encoding="utf-8") as fh:
            lines = fh.readlines()

        unpinned: list[str] = []
        for line in lines:
            if _is_comment_or_blank(line):
                continue
            # A pinned requirement looks like: package==X.Y.Z
            if "==" not in line:
                unpinned.append(line.strip())

        assert unpinned == [], (
            "The following lines in requirements.txt are not pinned with '==':\n"
            + "\n".join(f"  {ln}" for ln in unpinned)
        )


# ---------------------------------------------------------------------------
# SunbirdClient — ConfigurationError when token is absent
# ---------------------------------------------------------------------------


class TestSunbirdClientConfiguration:
    def test_raises_configuration_error_when_token_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SunbirdClient must raise ConfigurationError if SUNBIRD_API_TOKEN is unset."""
        monkeypatch.delenv("SUNBIRD_API_TOKEN", raising=False)

        from backend.sunbird_client import ConfigurationError, SunbirdClient

        with pytest.raises(ConfigurationError):
            SunbirdClient()
