"""Pytest configuration and shared fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require real DANE data (network).",
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run tests marked as slow.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="needs --run-integration")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="needs --run-slow")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


# ─── Shared fixtures ───────────────────────────────────────────────


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Path to the repo root."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def data_dir(project_root: Path) -> Path:
    """Path to the packaged data directory."""
    return project_root / "pulso" / "data"


@pytest.fixture(scope="session")
def schemas_dir(data_dir: Path) -> Path:
    return data_dir / "schemas"


@pytest.fixture(scope="session")
def fixtures_dir(project_root: Path) -> Path:
    return project_root / "tests" / "fixtures"
