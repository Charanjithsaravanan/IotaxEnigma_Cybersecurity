"""Backend adapter for the Docker behavioral sandbox."""

from __future__ import annotations

from typing import Any

from .sandbox_service import run_behavioral_scan


def run_sandbox(
    ecosystem: str, package_name: str, local_archive_path: str | None = None
) -> dict[str, Any]:
    """Run a registry-backed behavioral scan for the backend orchestrator."""
    return run_behavioral_scan(ecosystem, package_name, local_archive_path)