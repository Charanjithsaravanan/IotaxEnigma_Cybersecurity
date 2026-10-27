#!/usr/bin/env python3
"""Convert strace and runtime JSONL into the stable behavioral fingerprint."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

NOISE_PREFIXES = ("/usr/lib", "/usr/local/lib", "/lib", "/proc", "/sys", "/dev")
NOISE_EXACT = {"/etc/ld.so.cache", "/etc/ld.so.preload"}
NOISE_ENV = {"PATH", "PYTHONPATH", "NODE_PATH", "NODE_OPTIONS", "SANDBOX_RUNTIME_LOG"}


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _path_is_noise(path: str) -> bool:
    return path in NOISE_EXACT or path.startswith(NOISE_PREFIXES) or path.startswith("/proc/")


def _parse_strace(lines: Iterable[str]) -> dict[str, list[str]]:
    files: list[str] = []
    network: list[str] = []
    subprocesses: list[str] = []
    for line in lines:
        match = re.search(r"\b(?:openat2?|creat|unlinkat)\([^,]+,\s*\"([^\"]+)", line)
        if match:
            path = match.group(1)
            if not _path_is_noise(path) and not path.startswith("/etc/ld.so"):
                files.append(path)
        if re.search(r"\bconnect\(", line):
            host_match = re.search(r"sin_addr=inet_addr\(\"([^\"]+)\"\)|sin6_addr=inet_pton\(AF_INET6,\s*\"([^\"]+)\"", line)
            port_match = re.search(r"sin_port=htons\((\d+)\)", line)
            host = (host_match.group(1) or host_match.group(2)) if host_match else ""
            port = port_match.group(1) if port_match else None
            network.append(f"{host}:{port}" if port else host)
        match = re.search(r"\bexecve\(\"([^\"]+)\",\s*\[([^\]]*)\]", line)
        if match:
            args = re.findall(r'"([^"]*)"', match.group(2))
            if args and args[0] == match.group(1):
                args = args[1:]
            subprocesses.append(" ".join([match.group(1), *args]).strip())
    return {"files": _unique(files), "network": _unique(network), "subprocesses": _unique(subprocesses)}


def _parse_runtime(lines: Iterable[str]) -> dict[str, list[str]]:
    result = {"files": [], "network": [], "env": [], "subprocesses": []}
    for line in lines:
        try:
            event: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("event")
        if kind == "env_read" and event.get("key") not in NOISE_ENV:
            result["env"].append(str(event["key"]))
        elif kind in {"dns_lookup", "http_request"}:
            if kind == "dns_lookup":
                result["network"].append(str(event.get("host", "")))
            else:
                host = str(event.get("host", ""))
                port = event.get("port")
                result["network"].append(f"{host}:{port}" if host and port else host)
        elif kind == "socket_connect":
            result["network"].append(str(event.get("address", "")))
        elif kind == "subprocess":
            result["subprocesses"].append(str(event.get("command", "")))
    return {key: _unique(value) for key, value in result.items()}


def build_fingerprint(phase: str, strace_text: str, runtime_text: str) -> dict[str, dict[str, list[str]]]:
    parsed = _parse_strace(strace_text.splitlines())
    runtime = _parse_runtime(runtime_text.splitlines())
    values = {
        "network_calls": _unique(parsed["network"] + runtime["network"]),
        "files_touched": _unique(parsed["files"] + runtime["files"]),
        "env_vars_read": runtime["env"],
        "subprocesses_spawned": _unique(parsed["subprocesses"] + runtime["subprocesses"]),
    }
    empty = {"network_calls": [], "files_touched": [], "env_vars_read": [], "subprocesses_spawned": []}
    return {"install_time": values if phase == "install" else empty, "import_time": values if phase == "import" else empty}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("install", "import"), required=True)
    parser.add_argument("--strace", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--ecosystem", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--version", default="unknown")
    parser.add_argument("--sha256", default="")
    parser.add_argument("--duration-ms", type=int, default=0)
    parser.add_argument("--timed-out", action="store_true")
    parser.add_argument("--exit-code", type=int, default=0)
    args = parser.parse_args()
    fingerprint = build_fingerprint(
        args.phase,
        Path(args.strace).read_text(errors="replace"),
        Path(args.runtime).read_text(errors="replace"),
    )
    output = {
        "package": {"ecosystem": args.ecosystem, "name": args.name, "version": args.version, "sha256": args.sha256},
        "behavioral_fingerprint": fingerprint,
        "sandbox_metadata": {"duration_ms": args.duration_ms, "timed_out": args.timed_out, "exit_code": args.exit_code},
    }
    json.dump(output, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()