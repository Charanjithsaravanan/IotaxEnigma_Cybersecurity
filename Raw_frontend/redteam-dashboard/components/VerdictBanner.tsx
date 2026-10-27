import { AlertTriangle, ShieldAlert, ShieldCheck, ShieldX } from "lucide-react";
import type { Verdict } from "../types/scan";

const riskStyles = {
  low: {
    Icon: ShieldCheck,
    label: "SAFE",
    container:
      "border-green-300 bg-green-50 text-green-950 dark:border-green-800 dark:bg-green-950/40 dark:text-green-100",
    icon: "text-green-700 dark:text-green-400",
    detail: "text-green-800 dark:text-green-300",
  },
  medium: {
    Icon: ShieldAlert,
    label: "SUSPICIOUS",
    container:
      "border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100",
    icon: "text-amber-700 dark:text-amber-400",
    detail: "text-amber-800 dark:text-amber-300",
  },
  high: {
    Icon: ShieldX,
    label: "CRITICAL MISMATCH",
    container:
      "border-red-300 bg-red-50 text-red-950 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100",
    icon: "text-red-700 dark:text-red-400",
    detail: "text-red-800 dark:text-red-300",
  },
} as const;

export default function VerdictBanner({ verdict }: { verdict: Verdict }) {
  const style = riskStyles[verdict.risk];
  const RiskIcon = style.Icon;

  return (
    <section
      aria-label={`Scan verdict: ${style.label}`}
      className={`w-full rounded-xl border p-5 shadow-sm sm:p-6 ${style.container}`}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <RiskIcon aria-hidden="true" className={`size-7 shrink-0 ${style.icon}`} />
          <h2 className="text-base font-bold tracking-wide sm:text-lg">
            {style.label}
          </h2>
        </div>
        <p className="text-3xl font-bold tabular-nums sm:text-4xl">
          <span className="sr-only">Risk score </span>
          {verdict.score}
          <span className="text-lg font-semibold opacity-70 sm:text-xl">
            /100
          </span>
        </p>
      </div>

      {verdict.flags.length > 0 && (
        <ul className="mt-4 space-y-2 border-t border-current/15 pt-4">
          {verdict.flags.map((flag, index) => (
            <li
              key={`${flag}-${index}`}
              className={`flex items-start gap-2 text-sm ${style.detail}`}
            >
              <AlertTriangle
                aria-hidden="true"
                className="mt-0.5 size-4 shrink-0"
              />
              <span className="break-words">{flag}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
