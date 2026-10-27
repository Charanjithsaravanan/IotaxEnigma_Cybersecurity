"""Build an ephemeral package archive for a local sandbox scan."""

from __future__ import annotations

import io
import tarfile
import tempfile
from pathlib import Path


def build_local_archive(ecosystem: str, package_name: str, source: str, readme: str) -> tuple[str, str]:
    """Create a disposable PyPI or npm archive and return its path/import name."""
    safe_name = "".join(character if character.isalnum() or character in "-_" else "-" for character in package_name)
    import_name = safe_name.replace("-", "_")
    root = Path(tempfile.mkdtemp(prefix="pkgguard-upload-"))
    archive_path = root / f"{safe_name}.tar.gz"

    if ecosystem == "pypi":
        package_dir = root / "package" / import_name
        package_dir.mkdir(parents=True)
        (package_dir / "__init__.py").write_text(source, encoding="utf-8")
        (root / "package" / "README.md").write_text(readme, encoding="utf-8")
        (root / "package" / "setup.py").write_text(
            "from setuptools import setup\n"
            f"setup(name={package_name!r}, version='1.0.0', packages={[import_name]!r})\n",
            encoding="utf-8",
        )
    elif ecosystem == "npm":
        package_dir = root / "package"
        package_dir.mkdir()
        (package_dir / "index.js").write_text(source, encoding="utf-8")
        (package_dir / "README.md").write_text(readme, encoding="utf-8")
        (package_dir / "package.json").write_text(
            '{"name": ' + repr(package_name).replace("'", '"') +
            ', "version": "1.0.0", "main": "index.js"}',
            encoding="utf-8",
        )
    else:
        raise ValueError("ecosystem must be 'pypi' or 'npm'")

    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(root / "package", arcname="package")
    return str(archive_path), import_name
