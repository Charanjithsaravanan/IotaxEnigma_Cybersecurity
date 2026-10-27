# Traceguard

Traceguard is a behavioral supply-chain security prototype for Python and npm
packages. It runs package installation and import/require inside a restricted
Docker sandbox, records observable behavior, and compares that fingerprint with
the package's README and metadata.

It is designed to catch behavior such as:

- A string utility reading `~/.ssh/id_rsa`.
- An install script spawning `curl`, PowerShell, or another shell.
- An otherwise unrelated package reading `AWS_SECRET_ACCESS_KEY`.
- An HTTP client making network requests that are not documented.

## What is implemented

### Frontend

The Next.js dashboard is in
[`Raw_frontend/redteam-dashboard`](./Raw_frontend/redteam-dashboard).

- Supabase email/password sign-up and sign-in.
- Supabase Google and GitHub OAuth buttons.
- Local demo authentication when Supabase is not configured.
- A package submission screen for a package name, README, and Python source.
- Example safe, expected-network, and malicious cases.
- Calls the backend Docker sandbox when `NEXT_PUBLIC_API_URL` is configured.
- Browser-local fallback analysis when the backend is not configured.
- Scan detail pages showing claims, install events, import events, risk score,
  and mismatch flags.

### Backend

The FastAPI service is in [`pkgguard`](./pkgguard).

- `POST /api/local-scan` accepts pasted package content.
- A temporary PyPI-style archive is built from the submitted content.
- The archive is passed to the Docker sandbox for install and import/require
  execution.
- Network access is disabled in the sandbox.
- File access, environment reads, subprocesses, and network operations are
  traced.
- The deterministic analyzer returns a safe, suspicious, or malicious verdict.
- `REQUIRE_AUTH=true` makes the backend require a valid Supabase bearer token.

The existing registry scan endpoint is also available at `POST /api/scan` for
PyPI and npm package names. Registry scans require the Supabase persistence
tables described below. The current dashboard submission form sends
`ecosystem: "pypi"`; npm registry scans are available through the backend API
but are not currently selectable in that form.

## Requirements

- Windows 10/11, macOS, or Linux.
- Node.js 20 or newer.
- Python 3.10 or newer.
- Docker Desktop running with Linux containers enabled.
- A Supabase project for real authentication.
- Python dependencies from `pkgguard/ai_engine/requirements.txt` and the
  backend dependencies listed below.

The Docker sandbox is not a substitute for a production malware-analysis
environment. Use a disposable machine and do not provide real secrets to a
package under test.

## Supabase setup

1. Open [Supabase Dashboard](https://supabase.com/dashboard).
2. Create or open a project.
3. Go to **Project Settings → API**.
4. Copy the **Project URL** and the public **anon/publishable key**.
5. Do not use the `service_role` or `sb_secret_...` key in the frontend.
6. In **Authentication → Providers**, enable Email. Enable Google or GitHub
   only if their OAuth applications are configured.
7. In **Authentication → URL Configuration**, set the Site URL to:

```text
http://localhost:3000
```

Add this redirect URL if Supabase asks for one:

```text
http://localhost:3000/
```

Create the frontend environment file:

```text
Raw_frontend\redteam-dashboard\.env.local
```

```env
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_OR_PUBLISHABLE_KEY
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Email confirmation may be enabled by default. If enabled, a new user must
confirm their email before the first sign-in. For local-only testing, it can be
disabled under **Authentication → Providers → Email**.

### Optional persistence tables

The new pasted-package flow does not require database tables; it returns the
scan result directly from the backend. The older registry/cache flow uses
`packages` and `behavioral_scans`. Create those tables only when using
`POST /api/scan`:

```sql
create table if not exists public.packages (
  id uuid primary key default gen_random_uuid(),
  ecosystem text not null,
  name text not null,
  version text not null,
  sha256_hash text unique not null,
  readme_text text not null default '',
  claimed_intent jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.behavioral_scans (
  id uuid primary key default gen_random_uuid(),
  package_id uuid not null references public.packages(id),
  package_name text not null,
  ecosystem text not null,
  status text not null default 'sandboxing',
  install_trace jsonb,
  import_trace jsonb,
  risk_score integer,
  verdict text,
  mismatch_flags jsonb,
  llm_explanation text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.packages enable row level security;
alter table public.behavioral_scans enable row level security;
```

For production, use server-side policies or a service-role key only inside the
backend. Never expose a service-role key to Next.js.

## Run the frontend

Open PowerShell:

```powershell
cd "C:\Users\Charanjith\OneDrive\Desktop\Project\Raw_frontend\redteam-dashboard"
npm install
npm run dev
```

Open <http://localhost:3000>.

Sign in or create an account. Then:

1. Enter a package name.
2. Paste its README or metadata.
3. Paste a small Python module or trace note. The current dashboard submission
   form sends the content as a PyPI-style package.
4. Select **Run behavioral fingerprint**.
5. Review the scan result.

If `NEXT_PUBLIC_API_URL` is not present, the frontend uses its local browser
demo analyzer. If it is present, submission is sent to the Docker-backed
backend.

## Run the backend

Use a Windows Python interpreter. Open a new PowerShell window and run:

```powershell
$py = "C:\Users\Charanjith\AppData\Local\Python\pythoncore-3.14-64\python.exe"
cd "C:\Users\Charanjith\OneDrive\Desktop\Project\pkgguard"

& $py -m pip install -r ".\ai_engine\requirements.txt"
& $py -m pip install fastapi uvicorn httpx typer rich python-dotenv supabase
```

Set backend variables in the same PowerShell window that will run Uvicorn:

```powershell
$env:SUPABASE_URL = "https://YOUR_PROJECT_ID.supabase.co"
$env:SUPABASE_KEY = "YOUR_BACKEND_KEY"
$env:REQUIRE_AUTH = "true"
$env:USE_MOCK_MODULES = "false"
```

For a first local smoke test without authentication, use:

```powershell
$env:REQUIRE_AUTH = "false"
```

When `REQUIRE_AUTH=true`, the backend validates the access token sent by the
frontend with Supabase. Keep `SUPABASE_KEY` server-side; never put it in
`Raw_frontend\redteam-dashboard\.env.local`.

Start the API:

```powershell
& $py -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/docs> to inspect the API.

## Run the Docker sandbox

1. Start Docker Desktop.
2. Confirm Linux containers are active.
3. From the `pkgguard` directory, run:

```powershell
docker info
```

The first real scan builds the `behavioral-sandbox:latest` image from
[`pkgguard/sandbox/Dockerfile`](./pkgguard/sandbox/Dockerfile). The image
contains Python, Node.js, `strace`, and the tracing hooks.

The sandbox:

- Runs with `--network=none`.
- Uses a memory and CPU limit.
- Uses a disposable container for each phase.
- Provides canary credential files and environment variables for detection.
- Runs install and import phases separately.

If Docker is unavailable, the backend returns an explicit sandbox error rather
than silently claiming that a scan succeeded.

## Test the backend manually

With the API running and `REQUIRE_AUTH=false`:

```powershell
$body = @{
  ecosystem = "pypi"
  name = "demo-left-pad"
  readme = "A utility that pads strings and does not access the network."
  source = @'
def pad(value, width):
    return value.rjust(width)
'@
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/local-scan" `
  -ContentType "application/json" `
  -Body $body
```

To test suspicious behavior, replace `source` with:

```python
from pathlib import Path
import os
Path.home().joinpath(".ssh", "id_rsa").read_text()
os.environ.get("AWS_SECRET_ACCESS_KEY")
```

Run malicious examples only inside the Docker sandbox. Never run them directly
on your host.

## Complete local startup

Use three PowerShell windows.

### Window 1: Docker

Start Docker Desktop, then verify:

```powershell
docker info
```

### Window 2: Backend

```powershell
$py = "C:\Users\Charanjith\AppData\Local\Python\pythoncore-3.14-64\python.exe"
cd "C:\Users\Charanjith\OneDrive\Desktop\Project\pkgguard"

$env:SUPABASE_URL = "https://YOUR_PROJECT_ID.supabase.co"
$env:SUPABASE_KEY = "YOUR_BACKEND_KEY"
$env:REQUIRE_AUTH = "true"
$env:USE_MOCK_MODULES = "false"

& $py -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Check <http://127.0.0.1:8000/docs>.

### Window 3: Frontend

```powershell
cd "C:\Users\Charanjith\OneDrive\Desktop\Project\Raw_frontend\redteam-dashboard"
npm install
npm run dev
```

Open <http://localhost:3000>, select **Sign in**, create or use a Supabase
email/password account, then submit a package. The first sandbox request may
take several minutes while Docker builds the image.

If authentication is not configured yet, set `REQUIRE_AUTH=false` in Window 2.
The frontend can still run its local browser fallback if
`NEXT_PUBLIC_API_URL` is removed from `.env.local`, but that fallback does not
execute package code and is not a real sandbox scan.

## Deploy the backend to a Docker VPS

The current backend runs Docker commands for each package scan. Deploy it to a
Linux VPS with Docker installed, such as a DigitalOcean Droplet, Hetzner Cloud
server, AWS EC2 instance, or another Docker-capable host.

On the VPS:

```bash
git clone https://github.com/Charanjithsaravanan/IotaxEnigma_Cybersecurity.git
cd IotaxEnigma_Cybersecurity/pkgguard
docker build -t traceguard-api .
```

Create a backend `.env` file on the VPS. Do not commit it:

```env
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_KEY=YOUR_SERVER_SIDE_SUPABASE_KEY
REQUIRE_AUTH=true
USE_MOCK_MODULES=false
CORS_ORIGINS=https://iotax-enigma-cybersecurity.vercel.app
```

Run the API container with access to the VPS Docker daemon:

```bash
docker run -d \
  --name traceguard-api \
  --restart unless-stopped \
  --env-file .env \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  traceguard-api
```

Put the VPS behind HTTPS using Caddy, Nginx, or a cloud load balancer. The
public API URL should look like:

```text
https://api.your-domain.example
```

Verify the API:

```bash
curl https://api.your-domain.example/docs
```

Then add this environment variable in the Vercel project settings:

```text
NEXT_PUBLIC_API_URL=https://api.your-domain.example
```

Redeploy Vercel after saving the variable. The frontend will then send
authenticated scan requests to the VPS instead of using the browser-only
fallback.

For the deployed frontend at
<https://iotax-enigma-cybersecurity.vercel.app/>, the backend
`CORS_ORIGINS` value must include:

```text
https://iotax-enigma-cybersecurity.vercel.app
```

## Validation commands

Frontend:

```powershell
cd "C:\Users\Charanjith\OneDrive\Desktop\Project\Raw_frontend\redteam-dashboard"
npm run lint
npm run build
```

Backend:

```powershell
cd "C:\Users\Charanjith\OneDrive\Desktop\Project\pkgguard"
& $py -m compileall -q ai_engine backend sandbox shared
& $py -m unittest discover -s ai_engine -p "test*.py" -v
& $py -m unittest discover -s backend -p "test*.py" -v
```

## Important limitations

- The local pasted-package endpoint currently accepts Python source from the
  dashboard. The backend archive helper also supports npm archives, but the
  dashboard form does not expose an ecosystem selector yet.
- A Docker daemon is required for real behavior execution.
- The backend uses Supabase authentication validation when `REQUIRE_AUTH=true`,
  but production deployments should add rate limiting, request-size limits at
  the reverse proxy, structured audit logging, and a dedicated isolated worker.
- Do not use the current sandbox as a high-assurance malware isolation boundary.
- The local browser analyzer is a demonstration fallback, not evidence from
  executed package code.

## Project layout

```text
Project/
├── README.md
├── pkgguard/
│   ├── backend/
│   ├── ai_engine/
│   ├── sandbox/
│   └── shared/
└── Raw_frontend/
    └── redteam-dashboard/
        ├── app/
        ├── components/
        ├── hooks/
        └── lib/
```
