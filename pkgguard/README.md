# PkgGuard

PkgGuard is a behavioral supply-chain security prototype for Python and npm
packages. It compares a package's documented capabilities with the behavior
observed during installation and import/require.

The project combines:

- A FastAPI orchestration backend.
- An AI-assisted intent extraction and mismatch-scoring engine.
- A Docker-based behavioral sandbox.
- Shared Pydantic request, trace, and verdict models.
- A terminal client for scanning packages before installation.
- A Next.js dashboard for launching scans and displaying claims, traces,
  progress, and verdicts from the API.

> **Prototype warning:** PkgGuard executes package code in a sandbox for
> analysis. Do not treat the current configuration as production-grade
> isolation without applying the hardening recommendations in this document.

## Features

- Supports PyPI and npm package metadata lookup.
- Supports local package directories and local sandbox archives.
- Separates observed behavior into install-time and import-time phases.
- Records network calls, filesystem access, environment-variable reads, and
  subprocesses.
- Filters routine activity such as standard environment variables and standard
  library paths.
- Detects sensitive credential paths such as `.ssh`, `.aws`, and
  `.config/gcloud`.
- Detects undeclared `AWS_*` and `GITHUB_*` environment-variable reads.
- Produces a deterministic risk score from `0` to `100`.
- Optionally uses Gemini or Ollama for structured intent extraction and
  forensic explanations.
- Falls back to local heuristics when no LLM is configured.

## Repository layout

```text
pkgguard/
├── README.md
├── ai_engine/
│   ├── __init__.py
│   ├── analyzer.py
│   ├── prompts.py
│   ├── requirements.txt
│   └── test_member2.py
├── backend/
│   ├── __init__.py
│   ├── cli.py
│   ├── db.py
│   ├── main.py
│   └── registry.py
├── frontend/
├── pkg-sandbox/
├── sandbox/
│   ├── Dockerfile
│   ├── README.md
│   ├── create_test_packages.py
│   ├── node_preload.js
│   ├── parse_trace.py
│   ├── run_sandbox.py
│   ├── sandbox_service.py
│   ├── sitecustomize.py
│   └── trace_runner.sh
└── shared/
    ├── __init__.py
    └── schemas.py
```

### Component responsibilities

| Component | Responsibility |
|---|---|
| `ai_engine/` | Extracts claimed package intent and scores observed behavior |
| `backend/` | Fetches metadata, orchestrates scanning, persists results, and provides a CLI |
| `sandbox/` | Runs package installation/import inside Docker and parses telemetry |
| `shared/` | Defines models shared by the backend and orchestration layers |
| `frontend/` | Frontend application area |
| `pkg-sandbox/` | Additional sandbox-related project area |

## Requirements

### Windows development

- Windows 10 or later.
- Python 3.10 or later; Python 3.14 is supported by the current local setup.
- PowerShell.
- Python dependencies listed in `ai_engine/requirements.txt`.
- Docker Desktop if the real behavioral sandbox is used.
- Supabase credentials if database-backed API scans are used.

### Linux sandbox execution

The behavioral sandbox is designed for Ubuntu/Docker and requires:

- Ubuntu or another Linux host compatible with the scripts.
- Docker Engine.
- Python 3.10 or later.
- `jq` for convenient JSON inspection.
- `bash`, `node`, and `strace`.

The sandbox instructions are also available in
[`sandbox/README.md`](./sandbox/README.md).

## Installation

Open PowerShell and enter the combined project:

```powershell
cd "C:\Users\Charanjith\OneDrive\Desktop\Project iota\pkgguard"
```

Create a Windows virtual environment if you do not already have one:

```powershell
py -3 -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the interpreter directly instead:

```powershell
& ".\.venv\Scripts\python.exe" --version
```

Install the AI engine dependencies:

```powershell
python -m pip install -r ".\ai_engine\requirements.txt"
```

Install backend dependencies when running the FastAPI service or CLI:

```powershell
python -m pip install fastapi uvicorn httpx typer rich python-dotenv supabase
```

The repository may contain a local `.venv` created on another operating
system. A Linux ELF interpreter under `.venv/bin/` cannot be executed as a
normal Windows Python environment. If that occurs, create a Windows virtual
environment as shown above.

## Running the tests

Run all discovered Python tests from the project root:

```powershell
cd "C:\Users\Charanjith\OneDrive\Desktop\Project iota\pkgguard"
python -m unittest discover -s . -p "test*.py" -v
```

Expected result:

```text
Ran 4 tests
OK
```

If `python` is not the interpreter where the dependencies are installed,
replace `python` with its absolute path:

```powershell
& "C:\Path\To\python.exe" -m unittest discover -s . -p "test*.py" -v
```

The current AI engine tests are in
[`ai_engine/test_member2.py`](./ai_engine/test_member2.py). They cover:

1. Benign string utility behavior.
2. Documented HTTP-library behavior.
3. Installation-time network and subprocess activity.
4. Credential-path and secret-environment-variable access.

### Compile checks

```powershell
python -m compileall -q ai_engine backend sandbox shared
```

## Running the combined backend and frontend

Start the FastAPI service from the `pkgguard` directory:

```powershell
uvicorn backend.main:app --reload --port 8000
```

In a second PowerShell window, configure and start the dashboard:

```powershell
cd "C:\Users\Charanjith\OneDrive\Desktop\Project iota\frontend\IotaxEnigma\redteam-dashboard"
Add-Content .env.local "`nNEXT_PUBLIC_API_URL=http://localhost:8000"
npm run dev
```

Open `http://localhost:3000`, choose PyPI or npm, enter a package name, and
select **Start scan**. The dashboard calls `POST /api/scan`, then polls
`GET /api/scan/{scan_id}` while the persisted scan is still running.

### Import and deterministic fallback check

Clear LLM configuration so the local deterministic implementation is used:

```powershell
$env:GEMINI_API_KEY = ""
$env:OLLAMA_MODEL = ""

python -c "from ai_engine import BehavioralFingerprint, ClaimedIntent, evaluate_mismatch; print(evaluate_mismatch(ClaimedIntent(), BehavioralFingerprint()).model_dump())"
```

## AI engine usage

The public API is exported by [`ai_engine/__init__.py`](./ai_engine/__init__.py):

```python
from ai_engine import (
    BehavioralFingerprint,
    ClaimedIntent,
    evaluate_mismatch,
    extract_claimed_intent,
)
```

### Extract documented intent

```python
from ai_engine import extract_claimed_intent

claimed = extract_claimed_intent(
    readme_text="A utility that formats local text files.",
    metadata={
        "name": "example-package",
        "description": "A local text formatter",
    },
)

print(claimed.model_dump())
```

`ClaimedIntent` contains:

| Field | Description |
|---|---|
| `package_name` | Package name |
| `summary` | Package description |
| `expects_network` | Whether network activity is documented |
| `expects_file_read_outside_pkg` | Whether external filesystem access is documented |
| `expects_subprocess` | Whether subprocess execution is documented |
| `expects_env_reads` | Documented environment variables |
| `has_install_script` | Whether npm install scripts are present |

### Evaluate observed behavior

```python
from ai_engine import BehavioralFingerprint, evaluate_mismatch

observed = BehavioralFingerprint(
    install_time={
        "network_calls": [],
        "files_touched": [],
        "env_vars_read": [],
        "subprocesses_spawned": [],
    },
    import_time={
        "network_calls": [],
        "files_touched": ["/home/runner/.ssh/id_rsa"],
        "env_vars_read": ["AWS_SECRET_ACCESS_KEY"],
        "subprocesses_spawned": [],
    },
)

verdict = evaluate_mismatch(claimed, observed)
print(verdict.model_dump())
```

The result contains:

```json
{
  "risk_score": 100,
  "severity": "critical",
  "explanation": "...",
  "findings": [
    "The package touched a sensitive credential directory.",
    "The package read undeclared AWS or GitHub environment variables."
  ]
}
```

## Risk scoring

The deterministic scorer starts at zero and caps the final score at `100`.

| Observation | Points |
|---|---:|
| Network call during installation | +55 |
| Undocumented network call during import | +25 |
| Sensitive `.ssh`, `.aws`, or `.config/gcloud` path | +90 |
| Undeclared `AWS_*` or `GITHUB_*` environment read | +80 |
| Subprocess during installation | +40 |
| Undocumented subprocess during import | +25 |
| Undocumented non-standard filesystem access during import | +10 |

Severity mapping:

| Score | Severity |
|---:|---|
| 0–29 | `low` |
| 30–59 | `medium` |
| 60–79 | `high` |
| 80–100 | `critical` |

The analyzer filters routine activity before scoring:

- `PATH`, `HOME`, `LANG`, `PYTHONPATH`, and `NODE_ENV`.
- Files under `/usr/lib`, `/lib`, or paths containing `site-packages`.

The original input trace is not modified.

## Optional LLM configuration

The engine works without an LLM. With no provider configured, local heuristics
and deterministic scoring are used.

### Gemini

```powershell
$env:GEMINI_API_KEY = "your-api-key"
$env:GEMINI_MODEL = "gemini-2.0-flash"
```

### Ollama

```powershell
$env:GEMINI_API_KEY = ""
$env:OLLAMA_MODEL = "your-local-model"
```

Gemini takes precedence if both providers are configured. Do not commit API
keys or other secrets. Store local values in an ignored `.env` file when
appropriate.

## Backend API

The FastAPI application is defined in
[`backend/main.py`](./backend/main.py). Start it from the project root:

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The scan endpoint is:

```text
POST http://127.0.0.1:8000/api/scan
```

Example request:

```powershell
$body = @{
    ecosystem = "pypi"
    name = "requests"
    version = "latest"
    force_rescan = $false
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/api/scan" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

The request model is defined in
[`shared/schemas.py`](./shared/schemas.py):

```json
{
  "ecosystem": "pypi",
  "name": "package-name",
  "version": "latest",
  "force_rescan": false
}
```

Supported ecosystems are `pypi` and `npm`.

### Backend execution modes

By default, the backend uses mock adapters for standalone development:

```powershell
$env:USE_MOCK_MODULES = "true"
```

To use the real Docker sandbox and AI engine adapters:

```powershell
$env:USE_MOCK_MODULES = "false"
```

The backend adapter calls [`sandbox/runner.py`](./sandbox/runner.py), which
uses the same Docker service as the standalone sandbox CLI. Docker Desktop
must be installed and running when this mode is selected.

### Supabase configuration

The backend reads these variables through
[`backend/db.py`](./backend/db.py):

```text
SUPABASE_URL=...
SUPABASE_KEY=...
```

The backend stores package records and behavioral scan records in the
`packages` and `behavioral_scans` tables. Configure the database schema before
using cache-backed API scans.

## Command-line client

The terminal client is in [`backend/cli.py`](./backend/cli.py). Start the API
first, then run:

```powershell
python -m backend.cli install requests --eco pypi
```

Useful options:

```text
--eco, -e     Ecosystem: pypi or npm
--rescan, -r  Bypass the cached scan
```

The CLI displays:

- Documented capabilities.
- Install-time observations.
- Import-time observations.
- Risk score and verdict.
- Forensic findings.

Packages with a score of `70` or higher are blocked unless the user explicitly
overrides the policy.

## Behavioral sandbox

The sandbox runs package installation and import/require phases inside Docker.
It is intended for Linux hosts or Docker environments with the required Linux
tools.

### Build the image

From the `sandbox` directory on Linux:

```bash
cd sandbox
docker build --no-cache -t behavioral-sandbox:latest .
```

### Generate controlled test packages

```bash
python3 create_test_packages.py
```

This creates:

```text
sandbox/test-packages/benign_str_utils-0.1.0.tar.gz
sandbox/test-packages/evil_str_utils-0.1.0.tar.gz
```

The `evil_str_utils` archive is a controlled fixture for testing detection. It
is not a real malicious package.

### Run sandbox scans

```bash
python3 run_sandbox.py \
  pypi \
  benign-str-utils \
  --local-archive test-packages/benign_str_utils-0.1.0.tar.gz \
  > benign-result.json
```

```bash
python3 run_sandbox.py \
  pypi \
  evil-str-utils \
  --local-archive test-packages/evil_str_utils-0.1.0.tar.gz \
  > evil-result.json
```

Inspect the JSON results:

```bash
jq . benign-result.json
jq . evil-result.json
```

The sandbox documentation contains additional parser and Docker validation
commands in [`sandbox/README.md`](./sandbox/README.md).

## Trace contract

Each behavioral fingerprint contains two phases:

```json
{
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
}
```

Trace entries may be strings or dictionaries. The analyzer recognizes these
dictionary keys:

- Environment variables: `name`, `variable`, `env_var`, `key`.
- File paths: `path`, `file`, `filename`, `target`.

## Troubleshooting

### `ModuleNotFoundError: No module named 'pydantic'`

Install the AI engine requirements into the same interpreter used to run the
tests:

```powershell
python -m pip install -r ".\ai_engine\requirements.txt"
```

Confirm the interpreter:

```powershell
python -c "import sys; print(sys.executable)"
```

### The `.venv\bin\python3.14` executable does not run on Windows

That file may be a Linux ELF executable from a Linux virtual environment. Do
not use it as a Windows interpreter. Create or activate a Windows environment:

```powershell
py -3 -m venv .venv-windows
.\.venv-windows\Scripts\Activate.ps1
python -m pip install -r ".\ai_engine\requirements.txt"
```

### Backend cannot connect

Check that the API is running:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/docs
```

Then confirm that the CLI uses the same URL:

```text
http://localhost:8000/api/scan
```

### Docker sandbox does not start

Check Docker access:

```bash
docker ps
```

Then rebuild the image:

```bash
docker build --no-cache -t behavioral-sandbox:latest sandbox
```

## Security considerations

Before production use:

- Replace permissive Docker settings with a restrictive seccomp profile.
- Add AppArmor or SELinux policy enforcement.
- Drop unnecessary container capabilities.
- Run package code as a non-root user where possible.
- Keep secrets out of the sandbox and host environment.
- Restrict outbound network access and validate all package inputs.
- Replace wildcard CORS settings with an explicit allowlist.
- Add authentication and authorization to the API.
- Validate Supabase configuration and database permissions.
- Review all cached scan data before trusting it for installation decisions.

## Current limitations

- The deterministic classifier is keyword-based and can miss undocumented
  wording.
- Installation-time network and subprocess activity is currently treated as
  suspicious even when a package may legitimately need it.
- The analyzer only evaluates trace data supplied by the sandbox or caller.
- The backend depends on external Supabase configuration for persistent API
  scans. The AI engine and sandbox can still be tested independently without
  Supabase.
- The sandbox is a prototype and requires additional hardening before it can
  safely process arbitrary untrusted packages.

## License

No license file is currently included in this repository. Add an appropriate
license before distributing the project.
