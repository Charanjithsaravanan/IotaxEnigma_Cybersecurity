export interface ScanEvent {
  phase: "install" | "import";
  type: "network" | "file_read" | "env_read" | "subprocess";
  detail: string;
  severity: "normal" | "anomalous";
  timestamp: string;
}

export interface Claims {
  summary: string;
  allowed_capabilities: string[];
}

export interface Verdict {
  risk: "low" | "medium" | "high";
  score: number;
  flags: string[];
}

export interface Scan {
  id: string;
  package_name: string;
  status: "queued" | "installing" | "importing" | "analyzing" | "done";
  claims: Claims;
  events: ScanEvent[];
  verdict: Verdict;
  updated_at: string;
}
