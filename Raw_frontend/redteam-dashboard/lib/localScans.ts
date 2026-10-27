import type { Scan, ScanEvent } from "../types/scan";

const STORAGE_KEY = "traceguard:scans";

export interface ScanInput {
  packageName: string;
  readme: string;
  source: string;
}

export async function executeSandboxScan(input: ScanInput, accessToken?: string): Promise<Scan | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return null;

  const response = await fetch(`${apiUrl.replace(/\/$/, "")}/api/local-scan`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify({
      ecosystem: "pypi",
      name: input.packageName,
      readme: input.readme,
      source: input.source,
    }),
  });
  const payload = (await response.json()) as {
    detail?: string;
    scan_id: string;
    package: string;
    status: string;
    claimed_intent: { summary: string; expects_network: boolean; expects_file_read_outside_pkg: boolean; expects_subprocess: boolean; expects_env_reads: string[] };
    behavioral_fingerprint: {
      install_time: { network_calls: string[]; files_touched: string[]; env_vars_read: string[]; subprocesses_spawned: string[] };
      import_time: { network_calls: string[]; files_touched: string[]; env_vars_read: string[]; subprocesses_spawned: string[] };
    };
    verdict: { risk_score: number; verdict: "safe" | "suspicious" | "malicious"; mismatch_flags: string[] };
  };
  if (!response.ok) {
    throw new Error(payload.detail || "The sandbox could not analyze this package.");
  }

  const phases = payload.behavioral_fingerprint;
  const events: ScanEvent[] = [];
  for (const phase of ["install_time", "import_time"] as const) {
    const phaseName = phase === "install_time" ? "install" : "import";
    for (const detail of phases[phase].network_calls) events.push(event(phaseName, "network", detail, "anomalous"));
    for (const detail of phases[phase].files_touched) events.push(event(phaseName, "file_read", detail, /ssh|aws|credential|secret/i.test(detail) ? "anomalous" : "normal"));
    for (const detail of phases[phase].env_vars_read) events.push(event(phaseName, "env_read", detail, /secret|token|key/i.test(detail) ? "anomalous" : "normal"));
    for (const detail of phases[phase].subprocesses_spawned) events.push(event(phaseName, "subprocess", detail, "anomalous"));
  }
  return {
    id: payload.scan_id,
    package_name: payload.package,
    status: "done",
    claims: {
      summary: payload.claimed_intent.summary,
      allowed_capabilities: [
        ...(payload.claimed_intent.expects_network ? ["network"] : []),
        ...(payload.claimed_intent.expects_file_read_outside_pkg ? ["file_read"] : []),
        ...(payload.claimed_intent.expects_subprocess ? ["subprocess"] : []),
        ...(payload.claimed_intent.expects_env_reads.length ? ["env_read"] : []),
      ],
    },
    events,
    verdict: {
      risk: payload.verdict.verdict === "malicious" ? "high" : payload.verdict.verdict === "suspicious" ? "medium" : "low",
      score: payload.verdict.risk_score,
      flags: payload.verdict.mismatch_flags,
    },
    updated_at: new Date().toISOString(),
  };
}

function getStoredScans(): Scan[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored ? (JSON.parse(stored) as Scan[]) : [];
  } catch {
    return [];
  }
}

function saveScans(scans: Scan[]) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(scans));
  window.dispatchEvent(new CustomEvent("traceguard:scan-updated"));
}

export function getLocalScan(id: string): Scan | null {
  return getStoredScans().find((scan) => scan.id === id) ?? null;
}

function event(
  phase: ScanEvent["phase"],
  type: ScanEvent["type"],
  detail: string,
  severity: ScanEvent["severity"],
): ScanEvent {
  return {
    phase,
    type,
    detail,
    severity,
    timestamp: new Date().toISOString(),
  };
}

function analyzeInput(input: ScanInput): Pick<Scan, "claims" | "events" | "verdict"> {
  const text = `${input.packageName}\n${input.readme}\n${input.source}`.toLowerCase();
  const events: ScanEvent[] = [];
  const capabilities: string[] = [];
  const flags: string[] = [];
  let score = 0;

  const claimsNetwork = /(http|https|api|network|request|fetch|socket)/i.test(input.readme);
  const claimsFiles = /(file|filesystem|config|path|readme)/i.test(input.readme);
  const claimsSubprocess = /(subprocess|shell|command|cli|spawn)/i.test(input.readme);

  if (/(ssh|id_rsa|\.aws|credential|secret|private key)/i.test(text)) {
    events.push(event("import", "file_read", "Read a sensitive credential path outside the package directory", "anomalous"));
    flags.push("Accessed a sensitive credential path not declared in the package claims");
    score += 55;
  }

  if (/(aws_secret|github_token|api_key|access_token|secret_access_key)/i.test(text)) {
    events.push(event("import", "env_read", "Read a secret environment variable", "anomalous"));
    flags.push("Read a secret environment variable without declaring the capability");
    score += 45;
  }

  if (/(curl|wget|powershell|child_process|subprocess|exec\(|spawn\()/i.test(text)) {
    events.push(event("install", "subprocess", "Spawned an external process during package execution", "anomalous"));
    flags.push("Spawned a subprocess outside the documented package purpose");
    score += 35;
  }

  if (/(https?:\/\/|fetch\(|requests\.|axios|urllib|socket)/i.test(text)) {
    events.push(event("import", "network", "Attempted an outbound network request", claimsNetwork ? "normal" : "anomalous"));
    if (claimsNetwork) {
      capabilities.push("network");
    } else {
      flags.push("Made a network request that is not described in the README");
      score += 30;
    }
  }

  if (/(open\(|readfile|fs\.read|pathlib|\.read_text)/i.test(text)) {
    events.push(event("import", "file_read", "Touched a file outside the package runtime", claimsFiles ? "normal" : "anomalous"));
    if (claimsFiles) {
      capabilities.push("file_read");
    } else {
      flags.push("Read files without documenting filesystem access");
      score += 20;
    }
  }

  if (claimsSubprocess) {
    capabilities.push("subprocess");
  }

  score = Math.min(score, 100);
  const risk = score >= 70 ? "high" : score >= 30 ? "medium" : "low";

  return {
    claims: {
      summary: input.readme.trim().split("\n").find(Boolean) || "Package behavior submitted for analysis",
      allowed_capabilities: [...new Set(capabilities)],
    },
    events,
    verdict: {
      risk,
      score,
      flags,
    },
  };
}

export function createLocalScan(input: ScanInput): Scan {
  const scan: Scan = {
    id: crypto.randomUUID(),
    package_name: input.packageName.trim() || "unnamed-package",
    status: "done",
    ...analyzeInput(input),
    updated_at: new Date().toISOString(),
  };

  saveScans([scan, ...getStoredScans()].slice(0, 20));
  return scan;
}

export function seedExampleScans(scans: Scan[]) {
  const existing = getStoredScans();
  const seeded = scans.filter((scan) => !existing.some((item) => item.id === scan.id));
  if (seeded.length > 0) {
    saveScans([...seeded, ...existing]);
  }
}
