# PkgGuard AI Engine

This folder contains the Member 2 analysis engine for detecting whether a
Python or npm package's observed behavior is consistent with the behavior
claimed in its README and package metadata.

The engine compares:

1. **Claimed intent** - what the package says it does.
2. **Observed behavior** - actions captured by an external sandbox during
   installation and import.
3. **Deterministic security rules** - local rules that identify suspicious
   network access, credential access, environment-variable reads, subprocesses,
   and filesystem activity.
4. **Optional LLM analysis** - an additional structured explanation when
   Gemini or Ollama is configured.

The engine is a Python library. It does not contain a command-line entry point
or sandbox tracer; another part of the application must collect the runtime
trace and call this package.

## Folder contents

```text
Backend member 2 works/
├── README.md
├── ai_engine/
│   ├── __init__.py
│   ├── analyzer.py
│   ├── prompts.py
│   ├── requirements.txt
│   └── test_member2.py
└── .venv/                 # Local Python virtual environment, not source code
```

### `ai_engine/__init__.py`

Defines the public package interface. It re-exports these types and functions
from `analyzer.py`:

- `ClaimedIntent`
- `BehavioralFingerprint`
- `ScanVerdict`
- `extract_claimed_intent`
- `evaluate_mismatch`

Importing from `ai_engine` is therefore sufficient for normal use:

```python
from ai_engine import (
    BehavioralFingerprint,
    ClaimedIntent,
    evaluate_mismatch,
    extract_claimed_intent,
)
```

### `ai_engine/analyzer.py`

Contains the data models, optional LLM integration, local intent extraction,
trace filtering, deterministic scoring, severity mapping, and final verdict
generation. The complete process is described below.

### `ai_engine/prompts.py`

Contains the two system prompts used by the optional structured LLM calls:

- `INTENT_EXTRACTION_SYSTEM_PROMPT` tells the model how to classify a package's
  documented network, filesystem, subprocess, and environment-variable needs.
- `FORENSIC_VERDICT_SYSTEM_PROMPT` tells the model how to explain a mismatch
  using concrete paths, variables, IPs, URLs, or commands from the trace.

### `ai_engine/requirements.txt`

Declares the Python dependencies:

- `pydantic>=2.7` - validates input and output models.
- `langchain-core>=0.3` - builds structured prompt chains.
- `langchain-google-genai>=2.0` - optional Gemini provider.
- `langchain-ollama>=0.2` - optional local Ollama provider.

### `ai_engine/test_member2.py`

Contains four offline `unittest` smoke tests. The tests clear the LLM
configuration so they always exercise the deterministic local fallback:

1. A benign string utility produces a score of `0`.
2. A documented HTTP library is not penalized for standard-library file access.
3. Installation-time network access plus a subprocess produces a high score.
4. Credential-directory access plus secret environment-variable reads produces
   a critical score of `100`.

### `.venv`

This is the local Python virtual environment used to install dependencies and
run the code. It is an environment directory, not part of the engine's source
implementation. It should normally be excluded from source control.

## Complete execution flow

### 1. Package import

When `ai_engine` is imported:

1. `__init__.py` imports the public models and functions from `analyzer.py`.
2. `analyzer.py` imports Pydantic and the prompt constants.
3. No LLM is contacted during import.
4. No package is scanned during import; a caller must invoke one of the public
   functions.

### 2. Extract claimed intent

Call:

```python
claimed = extract_claimed_intent(readme_text, metadata)
```

The function performs these steps:

1. Converts the metadata to text.
2. Attempts to create an optional configured LLM provider.
3. If a provider is available, sends the package metadata and README to a
   structured-output chain using the `ClaimedIntent` schema.
4. If no provider is configured, a provider import fails, or the LLM request
   fails, logs a warning where appropriate and uses the local heuristic
   fallback.
5. Returns a validated `ClaimedIntent` model.

The `ClaimedIntent` fields are:

| Field | Meaning |
|---|---|
| `package_name` | Package name from `name` or `project_name` metadata |
| `summary` | Description from `description` or `summary` metadata |
| `expects_network` | Whether network activity is part of the documented purpose |
| `expects_file_read_outside_pkg` | Whether external filesystem access is documented |
| `expects_subprocess` | Whether invoking a CLI or subprocess is documented |
| `expects_env_reads` | Specific documented environment variables |
| `has_install_script` | Whether npm-style `preinstall`, `install`, or `postinstall` scripts exist |

#### Local intent heuristics

The fallback performs case-insensitive keyword checks:

- Network terms include `http request`, `api client`, `web scraping`, database
  drivers, cloud SDKs, telemetry, and remote assets.
- Filesystem terms include local files, configuration files, user files,
  filesystem access, and system logs.
- Subprocess terms include wrappers for `ffmpeg` or `git`, compiler tools, and
  task runners.
- Environment variables are extracted from README text when they look like
  uppercase names ending in `_API_KEY`, `_TOKEN`, `_URL`, `_SECRET`, `_HOST`,
  `_PORT`, or `_DEBUG`.

The local heuristic is intentionally conservative and should be replaced or
supplemented by the structured LLM result when an LLM is configured.

### 3. Validate observed behavior

The caller supplies a `BehavioralFingerprint`:

```python
actual = BehavioralFingerprint(
    install_time={
        "network_calls": [],
        "files_touched": [],
        "env_vars_read": [],
        "subprocesses_spawned": [],
    },
    import_time={
        "network_calls": [],
        "files_touched": [],
        "env_vars_read": [],
        "subprocesses_spawned": [],
    },
)
```

Each lifecycle phase is a `BehaviorTrace` with four lists:

- `network_calls`
- `files_touched`
- `env_vars_read`
- `subprocesses_spawned`

Each list item may be a string or a dictionary. The analyzer accepts common
dictionary keys:

- Environment names: `name`, `variable`, `env_var`, or `key`
- File paths: `path`, `file`, `filename`, or `target`

Pydantic validates the trace and supplies empty lists for omitted fields.
Unknown fields are ignored.

### 4. Filter routine activity

Before scoring, the analyzer copies each trace and removes activity considered
normal or non-suspicious:

- Standard environment variables:
  `PATH`, `HOME`, `LANG`, `PYTHONPATH`, and `NODE_ENV`
- Files under `/usr/lib`, `/lib`, or any path containing `site-packages`

Windows backslashes in file paths are normalized before path classification.
The original input model is not modified.

### 5. Calculate the deterministic risk score

Call:

```python
verdict = evaluate_mismatch(claimed, actual)
```

The local rules start at score `0` and add points for findings:

| Observed behavior | Score |
|---|---:|
| Any network call during installation | +55 |
| Import-time network call when network is not documented | +25 |
| Touching `.ssh`, `.aws`, or `.config/gcloud` | +90 |
| Reading undeclared variables beginning with `AWS_` or `GITHUB_` | +80 |
| Any subprocess during installation | +40 |
| Import-time subprocess when subprocess use is not documented | +25 |
| Import-time non-standard filesystem access when file access is not documented | +10 |

The final deterministic score is capped at `100`.

Important behavior:

- Documented network access prevents the import-time network penalty.
- Documented subprocess use prevents the import-time subprocess penalty.
- Documented external file access prevents the import-time filesystem penalty.
- Secret-variable reads remain suspicious unless the exact variable is listed
  in `claimed.expects_env_reads`.
- Installation-time network access and subprocess activity are always flagged
  by the current rules, regardless of claimed intent.

### 6. Map score to severity

The score becomes a severity label:

| Score | Severity |
|---:|---|
| `0-29` | `low` |
| `30-59` | `medium` |
| `60-79` | `high` |
| `80-100` | `critical` |

### 7. Optionally refine the explanation with an LLM

After deterministic scoring, `evaluate_mismatch` optionally sends the claimed
intent, observed behavior, and deterministic findings to the configured LLM.

The LLM must return `_SemanticAssessment`:

- `risk_score` from `0` to `100`
- `llm_explanation`
- optional `findings`

The deterministic score is always a lower bound:

```text
final score = max(deterministic score, LLM score)
```

The LLM cannot reduce a locally detected score. Its findings are merged with
the deterministic findings without duplicate entries. If the LLM is disabled
or fails, the local explanation and findings are returned.

### 8. Return the final verdict

`evaluate_mismatch` returns a `ScanVerdict` containing:

```python
{
    "risk_score": 0,
    "severity": "low",
    "explanation": "Observed behavior is consistent with the documented capabilities.",
    "findings": [],
}
```

For suspicious behavior, `findings` contains concise rule descriptions and
`explanation` contains either the joined local findings or the structured LLM
explanation.

## Optional LLM configuration

The engine works offline without an LLM. To use Gemini, set:

```powershell
$env:GEMINI_API_KEY = "your-key"
$env:GEMINI_MODEL = "gemini-2.0-flash"  # optional
```

To use Ollama instead, clear the Gemini key and set:

```powershell
$env:GEMINI_API_KEY = ""
$env:OLLAMA_MODEL = "your-local-model"
```

If both are set, Gemini takes precedence. If neither is set, the local
heuristics and deterministic scoring are used. Do not commit API keys or other
secrets to source control.

## Installation and setup

From PowerShell:

```powershell
cd "C:\Users\Charanjith\OneDrive\Desktop\Backend member 2 works"
.\.venv\Scripts\Activate.ps1
python -m pip install -r .\ai_engine\requirements.txt
```

If activation is not desired, invoke the virtual-environment interpreter
directly:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r ".\ai_engine\requirements.txt"
```

## Running the tests

Run the four offline tests:

```powershell
python -m unittest discover -s .\ai_engine -p "test_member2.py" -v
```

Expected result:

```text
Ran 4 tests
OK
```

Without activating the environment:

```powershell
& ".\.venv\Scripts\python.exe" -m unittest discover -s ".\ai_engine" -p "test_member2.py" -v
```

## Additional checks

Compile all Python files:

```powershell
python -m compileall -q .\ai_engine
```

Check the public import:

```powershell
python -c "from ai_engine import *; print('Import successful')"
```

The expected output is:

```text
Import successful
```

## Example end-to-end usage

```python
from ai_engine import (
    BehavioralFingerprint,
    evaluate_mismatch,
    extract_claimed_intent,
)

readme = "A utility that formats local text files."
metadata = {
    "name": "example-package",
    "description": "A local text formatter",
}

claimed = extract_claimed_intent(readme, metadata)
observed = BehavioralFingerprint(
    install_time={},
    import_time={
        "env_vars_read": ["AWS_SECRET_ACCESS_KEY"],
        "files_touched": ["/home/runner/.ssh/id_rsa"],
    },
)

verdict = evaluate_mismatch(claimed, observed)
print(verdict.model_dump())
```

The example should produce a critical verdict because the package reads an
undeclared AWS secret and touches a sensitive SSH credential path.

## Current scope and limitations

- The engine analyzes only the trace data supplied by its caller.
- It does not install packages, execute untrusted packages, or collect
  syscalls itself.
- It does not provide a CLI or web API.
- The local README classifier uses keyword matching and can miss wording that
  does not contain its known terms.
- The deterministic rules currently treat all installation-time network calls
  and subprocesses as suspicious, even when a package may legitimately need
  them.
- Sensitive-path detection covers `.ssh`, `.aws`, and `.config/gcloud`; other
  credential locations are not automatically recognized by the current rule.
- The optional LLM improves explanations but does not replace deterministic
  scoring.
