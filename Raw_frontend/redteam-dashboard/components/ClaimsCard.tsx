import { Check, FileText } from "lucide-react";
import type { Claims } from "../types/scan";
import { getCapabilityDisplay } from "../lib/formatCapability";

export default function ClaimsCard({ claims }: { claims: Claims }) {
  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 sm:p-6">
      <header className="flex items-center gap-2">
        <FileText
          aria-hidden="true"
          className="size-5 text-zinc-500 dark:text-zinc-400"
        />
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          What It Claims
        </h2>
      </header>

      <p className="mt-4 text-lg font-medium text-zinc-800 dark:text-zinc-200">
        Claims to be: {claims.summary}
      </p>

      <div className="mt-5">
        <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          Expected Capabilities
        </h3>
        <div className="mt-2 flex flex-wrap gap-2">
          {claims.allowed_capabilities.length === 0 ? (
            <span className="inline-flex items-center rounded-full bg-zinc-100 px-3 py-1 text-sm font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
              No special permissions claimed
            </span>
          ) : (
            claims.allowed_capabilities.map((capability, index) => (
              <span
                key={`${capability}-${index}`}
                className="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800 dark:bg-green-950 dark:text-green-300"
              >
                <Check aria-hidden="true" className="size-4" />
                {getCapabilityDisplay(capability).label}
              </span>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
