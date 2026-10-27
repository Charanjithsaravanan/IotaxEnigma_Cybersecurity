"""Host-side package acquisition and two-phase Docker sandbox orchestration."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
IMAGE = os.environ.get("SANDBOX_IMAGE", "behavioral-sandbox:latest")
TIMEOUT_SECONDS = 30


def _docker_command() -> str:
    command = shutil.which("docker")
    if command:
        return command
    windows_path = Path(
        os.environ.get("ProgramFiles", r"C:\Program Files")
    ) / "Docker" / "Docker" / "resources" / "bin" / "docker.exe"
    if windows_path.is_file():
        return str(windows_path)
    raise FileNotFoundError(
        "Docker CLI was not found. Install Docker Desktop and start its daemon."
    )


def _download(ecosystem: str, name: str, destination: Path) -> tuple[Path, str]:
    if ecosystem == "pypi":
        metadata = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json", timeout=15))
        version = metadata["info"]["version"]
        files = metadata["releases"][version]
        chosen = next((item for item in files if item["filename"].endswith((".whl", ".tar.gz"))), files[0])
        target = destination / chosen["filename"]
        urllib.request.urlretrieve(chosen["url"], target)
        return target, version
    if ecosystem == "npm":
        metadata = json.load(urllib.request.urlopen(f"https://registry.npmjs.org/{urllib.parse.quote(name)}", timeout=15))
        version = metadata["dist-tags"]["latest"]
        target = destination / f"{name.replace('/', '-')}-{version}.tgz"
        urllib.request.urlretrieve(metadata["versions"][version]["dist"]["tarball"], target)
        return target, version
    raise ValueError("ecosystem must be 'pypi' or 'npm'")


def _archive_version(path: Path, ecosystem: str) -> str:
    if ecosystem == "npm":
        with tarfile.open(path, "r:*") as archive:
            member = next((m for m in archive.getmembers() if m.name.endswith("package/package.json")), None)
            if member:
                extracted = archive.extractfile(member)
                if extracted:
                    return str(json.load(extracted).get("version", "unknown"))
    elif path.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(path, "r:*") as archive:
            metadata = next((m for m in archive.getmembers() if m.name.endswith("/PKG-INFO")), None)
            if metadata:
                extracted = archive.extractfile(metadata)
                if extracted:
                    for line in extracted.read().decode(errors="replace").splitlines():
                        if line.lower().startswith("version:"):
                            return line.split(":", 1)[1].strip()
    elif path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            metadata = next((n for n in archive.namelist() if n.endswith(".dist-info/METADATA")), None)
            if metadata:
                for line in archive.read(metadata).decode(errors="replace").splitlines():
                    if line.lower().startswith("version:"):
                        return line.split(":", 1)[1].strip()
    return "unknown"


def _run_phase(
    ecosystem: str,
    package: str,
    import_name: str,
    archive: Path,
    phase: str,
    logs: Path,
    install_state: Path,
) -> tuple[int, bool, int]:
    container_name = f"behavioral-sandbox-{phase}-{uuid.uuid4().hex[:12]}"
    command = [
        _docker_command(), "run", "--rm", "--network=none", "--cap-add=SYS_PTRACE",
        "--security-opt", "seccomp=unconfined", "--memory=512m", "--cpus=1.0",
        "--name", container_name,
        "-e", f"SANDBOX_PHASE={phase}", "-v", f"{archive.parent}:/input:ro",
        "-v", f"{logs}:/logs",         "-v",
        f"{install_state}:{'/app/npm-project' if ecosystem == 'npm' else '/app/site-packages'}",
        IMAGE, ecosystem, f"/input/{archive.name}", package, import_name,
    ]
    started = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
        (logs / f"docker.{phase}.stdout").write_text(stdout or "")
        (logs / f"docker.{phase}.stderr").write_text(stderr or "")
        if process.returncode:
            print(f"{phase} phase failed (exit {process.returncode}): {(stderr or stdout).strip()}", file=sys.stderr)
        return process.returncode or 0, False, int((time.monotonic() - started) * 1000)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        (logs / f"docker.{phase}.stdout").write_text(stdout or "")
        (logs / f"docker.{phase}.stderr").write_text(stderr or "")
        subprocess.run(
            [_docker_command(), "rm", "--force", container_name],
            check=False,
            capture_output=True,
        )
        return 124, True, int((time.monotonic() - started) * 1000)


def run_behavioral_scan(ecosystem: str, package_name: str, local_archive_path: str | None = None) -> dict[str, Any]:
    """Return a strict behavioral fingerprint for a PyPI or npm archive."""
    ecosystem = ecosystem.lower()
    if ecosystem not in {"pypi", "npm"}:
        raise ValueError("ecosystem must be 'pypi' or 'npm'")
    with tempfile.TemporaryDirectory(prefix="behavioral-scan-") as work:
        root = Path(work)
        if local_archive_path:
            source = Path(local_archive_path).resolve()
            if not source.is_file():
                raise FileNotFoundError(local_archive_path)
            archive = root / source.name
            archive.write_bytes(source.read_bytes())
            version = _archive_version(archive, ecosystem)
        else:
            archive, version = _download(ecosystem, package_name, root)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        logs = root / "logs"
        logs.mkdir()
        install_state = root / "site-packages"
        install_state.mkdir()
        if ecosystem == "npm":
            install_state = root / "npm-project"
            install_state.mkdir()
        build = subprocess.run(
            [_docker_command(), "build", "--tag", IMAGE, str(ROOT)],
            check=False,
            capture_output=True,
            text=True,
        )
        if build.returncode != 0:
            details = (build.stderr or build.stdout).strip()
            raise RuntimeError(f"Docker image build failed (exit {build.returncode}): {details}")
        import_name = package_name.split("/")[-1].replace("-", "_") if ecosystem == "pypi" else package_name
        install_code, install_timeout, install_ms = _run_phase(
            ecosystem, package_name, import_name, archive, "install", logs, install_state
        )
        import_code, import_timeout, import_ms = _run_phase(
            ecosystem, package_name, import_name, archive, "import", logs, install_state
        )
        try:
            from .parse_trace import build_fingerprint
        except ImportError:
            from parse_trace import build_fingerprint

        def _read_log(name: str) -> str:
            path = logs / name
            return path.read_text(errors="replace") if path.exists() else ""

        install = build_fingerprint(
            "install",
            _read_log("strace.install.log"),
            _read_log("runtime.install.jsonl"),
        )
        imported = build_fingerprint(
            "import",
            _read_log("strace.import.log"),
            _read_log("runtime.import.jsonl"),
        )
        return {
            "package": {"ecosystem": ecosystem, "name": package_name, "version": version, "sha256": digest},
            "behavioral_fingerprint": {"install_time": install["install_time"], "import_time": imported["import_time"]},
            "sandbox_metadata": {
                "duration_ms": install_ms + import_ms,
                "timed_out": install_timeout or import_timeout,
                "exit_code": import_code if import_code else install_code,
            },
        }
