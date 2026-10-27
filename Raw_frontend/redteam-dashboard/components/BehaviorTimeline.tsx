"use client";

import {
  Activity,
  CircleHelp,
  FileKey,
  FileText,
  FileWarning,
  Globe,
  KeyRound,
  Network,
  Terminal,
  type LucideIcon,
} from "lucide-react";
import { startTransition, useEffect, useRef, useState } from "react";
import {
  getCapabilityDisplay,
  type CapabilityIconName,
} from "../lib/formatCapability";
import type { ScanEvent } from "../types/scan";

const icons: Record<CapabilityIconName, LucideIcon> = {
  Globe,
  FileKey,
  FileText,
  Network,
  FileWarning,
  KeyRound,
  Terminal,
  CircleHelp,
};

const timestampFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZone: "UTC",
});

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);

  return Number.isNaN(date.getTime())
    ? timestamp
    : timestampFormatter.format(date);
}

export default function BehaviorTimeline({
  events,
}: {
  events: ScanEvent[];
}) {
  const [activePhase, setActivePhase] = useState<ScanEvent["phase"]>(() => {
    const hasInstallEvents = events.some((event) => event.phase === "install");
    const hasImportEvents = events.some((event) => event.phase === "import");

    return hasInstallEvents || !hasImportEvents ? "install" : "import";
  });
  const previousEventsLength = useRef(events.length);
  const [newestEventIndex, setNewestEventIndex] = useState<number | null>(null);

  const activeEvents = events.filter((event) => event.phase === activePhase);

  useEffect(() => {
    if (events.length > previousEventsLength.current) {
      const appendedIndex = events.length - 1;
      startTransition(() => setNewestEventIndex(appendedIndex));
    } else if (events.length < previousEventsLength.current) {
      startTransition(() => setNewestEventIndex(null));
    }
    previousEventsLength.current = events.length;
  }, [events]);

  return (
    <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 sm:p-6">
      <header className="flex items-center gap-2">
        <Activity
          aria-hidden="true"
          className="size-5 text-zinc-500 dark:text-zinc-400"
        />
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">
          What It Actually Did
        </h2>
      </header>

      <div
        aria-label="Behavior phase"
        className="mt-5 flex w-full gap-1 rounded-lg bg-zinc-100 p-1 dark:bg-zinc-800"
        role="tablist"
      >
        {(["install", "import"] as const).map((phase) => {
          const isActive = activePhase === phase;
          const label = phase === "install" ? "Install Time" : "Import Time";

          return (
            <button
              key={phase}
              aria-controls="behavior-events"
              aria-selected={isActive}
              className={`min-h-10 flex-1 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-zinc-100"
                  : "text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
              }`}
              id={`behavior-tab-${phase}`}
              onClick={() => setActivePhase(phase)}
              role="tab"
              type="button"
            >
              {label}
            </button>
          );
        })}
      </div>

      <div
        aria-labelledby={`behavior-tab-${activePhase}`}
        className="mt-5"
        id="behavior-events"
        role="tabpanel"
      >
        {activeEvents.length === 0 ? (
          <div className="flex min-h-24 flex-col items-center justify-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
            <Activity aria-hidden="true" className="size-5 opacity-60" />
            <p>No activity recorded</p>
          </div>
        ) : (
          <ol className="space-y-3">
            {activeEvents.map((event, index) => {
              const eventIndex = events.indexOf(event);
              const { iconName } = getCapabilityDisplay(event.type);
              const EventIcon = icons[iconName];
              const isAnomalous = event.severity === "anomalous";
              const isNewestEvent = eventIndex === newestEventIndex;

              return (
                <li
                  key={`${event.timestamp}-${event.type}-${index}`}
                  onAnimationEnd={() => {
                    if (isNewestEvent) {
                      setNewestEventIndex(null);
                    }
                  }}
                  className={`flex min-w-0 gap-3 rounded-lg border-l-4 p-3 ${
                    isAnomalous
                      ? "border-red-500 bg-red-50 dark:border-red-400 dark:bg-red-950/40"
                      : "border-zinc-300 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800/60"
                  }${isNewestEvent ? " animate-fade-in-up" : ""}`}
                >
                  <EventIcon
                    aria-hidden="true"
                    className={`mt-0.5 size-5 shrink-0 ${
                      isAnomalous
                        ? "text-red-600 dark:text-red-400"
                        : "text-zinc-500 dark:text-zinc-400"
                    }`}
                  />
                  <div className="min-w-0 flex-1">
                    <p
                      className={`break-words text-sm ${
                        isAnomalous
                          ? "text-red-900 dark:text-red-200"
                          : "text-zinc-800 dark:text-zinc-200"
                      }`}
                    >
                      {event.detail}
                    </p>
                    <time
                      className={`mt-1 block text-xs ${
                        isAnomalous
                          ? "text-red-700 dark:text-red-300"
                          : "text-zinc-500 dark:text-zinc-400"
                      }`}
                      dateTime={event.timestamp}
                    >
                      {formatTimestamp(event.timestamp)}
                    </time>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </section>
  );
}
