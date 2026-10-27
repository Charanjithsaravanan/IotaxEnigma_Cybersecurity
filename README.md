# Traceguard

Traceguard is a behavioral supply-chain security prototype for Python and npm
packages. It runs package installation and import/require inside a restricted
Docker sandbox, records observable behavior, and compares that fingerprint with
the package's README and metadata.

**Live website:** <https://iotax-enigma-cybersecurity.vercel.app/>

It is designed to catch behavior such as:

- A string utility reading `~/.ssh/id_rsa`.
- An install script spawning `curl`, PowerShell, or another shell.
- An otherwise unrelated package reading `AWS_SECRET_ACCESS_KEY`.
- An HTTP client making network requests that are not documented.

## How to open and use the website

1. Open <https://iotax-enigma-cybersecurity.vercel.app/> in any modern browser.
2. Select **Sign in** and create an account (email/password, Google, or GitHub).
   If email confirmation is enabled, confirm your email before signing in.
3. Enter a package name.
4. Paste the package's README or metadata.
5. Paste a small Python module or trace note.
6. Select **Run behavioral fingerprint**.
7. Review the result: claims, install events, import events, risk score, and
   mismatch flags.

You can also try the built-in example cases (safe, expected-network, and
malicious).

If the backend is not connected to the deployed site, the website falls back to
a browser-only demo analyzer. That fallback does not execute package code and is
not a real sandbox scan.

## What is implemented

### Frontend

The Next.js dashboard is in `Raw_frontend/redteam-dashboard`.

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

The FastAPI service is in `pkgguard`.

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

## Running locally (optional)

Only needed if you want to run your own copy instead of using the live website.

### Requirements

- Windows 10/11, macOS, or Linux.
- Node.js 20 or newer.
- Python 3.10 or newer.
- Docker Desktop (or Docker Engine) running with Linux containers enabled.
- A Supabase project for real authentication.
- Python dependencies from `pkgguard/ai_engine/requirements.txt` and the
  backend dependencies listed below.

The Docker sandbox is not a substitute for a production malware-analysis
environment. Use a disposable machine and do not provide real secrets to a
package under test.

### Supabase setup

1. Open [Supabase Dashboard](https://supabase.com/dashboard).
2. Create or open a project.
3. Go to **Project Settings → API**.
4. Copy the **Project URL** and the public **anon/publishable key**.
5. Do not use the `service_role` or `sb_secret_...` key in the frontend.
6. In **Authentication → Providers**, enable Email. Enable Google or GitHub
   only if their OAuth applications are configured.
7. In **Authentication → URL Configuration**, set the Site URL to
   `http://localhost:3000` (and add `http://localhost:3000/` as a redirect URL
   if Supabase asks for one).

Create `.env.local` inside `Raw_frontend/redteam-dashboard`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_OR_PUBLISHABLE_KEY
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Email confirmation may be enabled by default. If enabled, a new user must
confirm their email before the first sign-in. For local-only testing, it can be
disabled under **Authentication → Providers → Email**.

### Optional persistence tables

The pasted-package flow does not require database tables; it returns the scan
result directly from the backend. The older registry/cache flow uses `packages`
and `behavioral_scans`. Create those tables only when using `POST /api/scan`:

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

### Start everything

Use three terminal windows, starting from the repository root.

**Terminal 1: Docker**

Start Docker, then verify it is running:

```bash
docker info
```

The first real scan builds the `behavioral-sandbox:latest` image from
`pkgguard/sandbox/Dockerfile`. The image contains Python, Node.js, `strace`,
and the tracing hooks. If Docker is unavailable, the backend returns an
explicit sandbox error rather than silently claiming that a scan succeeded.

**Terminal 2: Backend**

```bash
cd pkgguard
python -m pip install -r ai_engine/requirements.txt
python -m pip install fastapi uvicorn httpx typer rich python-dotenv supabase
```

Set the backend variables in the same terminal that will run Uvicorn.

PowerShell (Windows):

```powershell
$env:SUPABASE_URL = "https://YOUR_PROJECT_ID.supabase.co"
$env:SUPABASE_KEY = "YOUR_BACKEND_KEY"
$env:REQUIRE_AUTH = "true"
$env:USE_MOCK_MODULES = "false"
```

macOS / Linux:

```bash
export SUPABASE_URL="https://YOUR_PROJECT_ID.supabase.co"
export SUPABASE_KEY="YOUR_BACKEND_KEY"
export REQUIRE_AUTH="true"
export USE_MOCK_MODULES="false"
```

For a first smoke test without authentication, set `REQUIRE_AUTH` to `false`.
When `REQUIRE_AUTH=true`, the backend validates the access token sent by the
frontend with Supabase. Keep `SUPABASE_KEY` server-side; never put it in the
frontend `.env.local`.

Start the API:

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000/docs> to inspect the API.

**Terminal 3: Frontend**

```bash
cd Raw_frontend/redteam-dashboard
npm install
npm run dev
```

Open <http://localhost:3000>, sign in, and submit a package. The first sandbox
request may take several minutes while Docker builds the image.

If `NEXT_PUBLIC_API_URL` is removed from `.env.local`, the frontend uses its
browser-only fallback, which does not execute package code.

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

## Deploy the backend to a Docker VPS

The backend runs Docker commands for each package scan. Deploy it to a Linux VPS
with Docker installed, such as a DigitalOcean Droplet, Hetzner Cloud server, AWS
EC2 instance, or another Docker-capable host.

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
public API URL should look like `https://api.your-domain.example`. Verify it:

```bash
curl https://api.your-domain.example/docs
```

Then add this environment variable in the Vercel project settings:

```text
NEXT_PUBLIC_API_URL=https://api.your-domain.example
```

Redeploy Vercel after saving the variable. The deployed frontend at
<https://iotax-enigma-cybersecurity.vercel.app/> will then send authenticated
scan requests to the VPS instead of using the browser-only fallback. The backend
`CORS_ORIGINS` value must include
`https://iotax-enigma-cybersecurity.vercel.app`.

## Validation commands

Frontend (from `Raw_frontend/redteam-dashboard`):

```bash
npm run lint
npm run build
```

Backend (from `pkgguard`):

```bash
python -m compileall -q ai_engine backend sandbox shared
python -m unittest discover -s ai_engine -p "test*.py" -v
python -m unittest discover -s backend -p "test*.py" -v
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
