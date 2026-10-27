"use client";

import type { Scan } from "../types/scan";

const progressByStatus: Record<Scan["status"], number> = {
  queued: 10,
  installing: 35,
  importing: 65,
  analyzing: 85,
  done: 100,
};

const labels: Record<Scan["status"], string> = {
  queued: "Queued...",
  installing: "Installing...",
  importing: "Importing...",
  analyzing: "Analyzing...",
  done: "Done",
};

export default function ScanProgressBar({
  status,
}: {
  status: Scan["status"];
}) {
  const progress = progressByStatus[status];
  const isDone = status === "done";

  return (
    <section
      aria-label="Scan progress"
      className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 sm:p-5"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          {labels[status]}
        </h2>
        <span className="text-sm tabular-nums text-zinc-500 dark:text-zinc-400">
          {progress}%
        </span>
      </div>
      <div
        aria-label={labels[status]}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={progress}
        className="h-2.5 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-700"
        role="progressbar"
      >
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${
            isDone
              ? "bg-green-500 dark:bg-green-400"
              : "animate-pulse bg-blue-500 dark:bg-blue-400"
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </section>
  );
}
