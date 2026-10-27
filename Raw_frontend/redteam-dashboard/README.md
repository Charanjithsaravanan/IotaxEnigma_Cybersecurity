# Member 4 — Red-Team Demo Dashboard

Frontend dashboard that visualizes "what a package claims" vs "what it actually
did" during a scan, driven live by Supabase Realtime. Also includes 4 Python
demo packages for testing the pipeline end to end.

## Folder structure

```
member4-frontend/
  redteam-dashboard/     Next.js app (dashboard)
  demo-packages/         4 sample pip packages for testing
```

## Running the dashboard

```bash
cd redteam-dashboard
npm install
npm run dev
```

Open `http://localhost:3000`.

The dashboard now works in local demo mode without Supabase credentials:

1. Open the home page and choose **Paste package**.
2. Enter a package name, README/metadata, and a small source file or trace note.
3. Select **Run behavioral fingerprint**.
4. Review the claims, observed install/import events, risk score, and mismatch flags.

Use **Try a case** to load the clean utility, expected-network, or credential-theft
examples. Submitted scans are stored in the browser's local storage so the flow
can be demonstrated without a backend.

## Environment variables

Create `redteam-dashboard/.env.local` (not included in this zip — ask the
team lead or Supabase project owner for these values):

```
NEXT_PUBLIC_SUPABASE_URL=your-project-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

Restart `npm run dev` after adding/changing this file.

When these variables are present, scan detail pages also subscribe to the
Supabase `scans` table through Realtime. Without them, the local demo scan
storage remains active.

## Supabase `scans` table schema

The backend should write scan progress to this table — the dashboard
subscribes to it via Realtime and updates live, no page refresh needed.

```sql
create table scans (
  id uuid primary key default gen_random_uuid(),
  package_name text not null,
  status text not null default 'queued',  -- queued | installing | importing | analyzing | done
  claims jsonb,       -- { summary: string, allowed_capabilities: string[] }
  events jsonb[],     -- [{ phase, type, detail, severity, timestamp }, ...]
  verdict jsonb,       -- { risk: 'low'|'medium'|'high', score: number, flags: string[] }
  updated_at timestamptz default now()
);

alter publication supabase_realtime add table scans;
```

Capability/event type values used by the UI: `network`, `file_read`,
`file_sensitive`, `file_general`, `env_read`, `env_secrets`, `subprocess`.
Severity values: `normal`, `anomalous`.

To push a live scan, the backend inserts a row with `status: 'queued'`, then
updates that same row's `status`/`events`/`verdict` as the scan progresses.
The dashboard reads scan by `id` at `/scan/<uuid>`.

## Demo packages

Four real pip-installable packages used to prove the pipeline works, found in
`demo-packages/`:

| Package | Claims to be | Actually does | Expected verdict |
|---|---|---|---|
| `clean-left-pad` | string padding utility | pure string ops, no I/O | SAFE (score 0) |
| `http-fetcher` | HTTP client | makes an HTTP call (matches claim) | SAFE (score 5) |
| `evil-left-pad` | string padding utility | on install: reads `~/.ssh/id_rsa`, spawns `curl` | CRITICAL (score 98) |
| `color-logger-pro` | terminal colorizer | on import: reads `AWS_SECRET_ACCESS_KEY`, makes a network call | CRITICAL (score 95) |

Test each locally:
```bash
cd demo-packages/<name>
python -m pip install -e .
python -c "import <module_name>"
```

## What's done

- Split-screen view: claims card (left) vs behavior timeline (right), tabbed
  by install/import phase
- Verdict banner (SAFE / SUSPICIOUS / CRITICAL) with score and flags
- Live progress bar + animated event feed via Supabase Realtime
- All 4 demo packages install and behave as described above

## What's needed from the rest of the pipeline

The backend (sandbox + tracer + comparator) needs to write to the `scans`
table in the shape above as a real scan runs, so the dashboard can point at a
real `id` instead of the manually-inserted test rows used during development.