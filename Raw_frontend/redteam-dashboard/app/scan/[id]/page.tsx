"use client";

import { Suspense } from "react";
import { useParams } from "next/navigation";
import BehaviorTimeline from "../../../components/BehaviorTimeline";
import ClaimsCard from "../../../components/ClaimsCard";
import ScanProgressBar from "../../../components/ScanProgressBar";
import VerdictBanner from "../../../components/VerdictBanner";
import { useScanRealtime } from "../../../hooks/useScanRealtime";

export default function ScanPage() {
  return (
    <Suspense fallback={<ScanLoading />}>
      <ScanContent />
    </Suspense>
  );
}

function ScanLoading() {
  return (
    <main
      aria-label="Loading scan"
      className="min-h-full flex-1 bg-zinc-50 px-4 py-8 dark:bg-black sm:px-6 sm:py-12"
      role="status"
    >
      <div className="mx-auto w-full max-w-6xl animate-pulse space-y-6">
        <div className="h-10 w-64 rounded-lg bg-zinc-200 dark:bg-zinc-800" />
        <div className="h-32 rounded-xl bg-zinc-200 dark:bg-zinc-800" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="h-56 rounded-xl bg-zinc-200 dark:bg-zinc-800" />
          <div className="h-56 rounded-xl bg-zinc-200 dark:bg-zinc-800" />
        </div>
      </div>
    </main>
  );
}

function ScanContent() {
  const params = useParams<{ id: string }>();
  const scanId = Array.isArray(params.id) ? params.id[0] : params.id;
  const { scan, loading, error } = useScanRealtime(scanId);

  if (loading) {
    return <ScanLoading />;
  }

  if (error) {
    return (
      <main className="flex min-h-full flex-1 items-center justify-center bg-zinc-50 px-4 py-12 text-zinc-950 dark:bg-black dark:text-zinc-50">
        <p
          className="max-w-xl text-center text-base text-red-700 dark:text-red-400"
          role="alert"
        >
          Unable to load scan: {error}
        </p>
      </main>
    );
  }

  if (!scan) {
    return (
      <main className="flex min-h-full flex-1 items-center justify-center bg-zinc-50 px-4 py-12 text-zinc-950 dark:bg-black dark:text-zinc-50">
        <p className="text-center text-lg font-medium text-zinc-600 dark:text-zinc-400">
          Scan not found
        </p>
      </main>
    );
  }

  return (
    <main className="min-h-full flex-1 bg-zinc-50 px-4 py-8 text-zinc-950 dark:bg-black dark:text-zinc-50 sm:px-6 sm:py-12">
      <div className="mx-auto w-full max-w-6xl">
        <header className="mb-6 flex flex-wrap items-center gap-3 sm:mb-8">
          <h1 className="break-words text-3xl font-bold tracking-tight sm:text-4xl">
            {scan.package_name}
          </h1>
          <span className="inline-flex items-center rounded-full bg-zinc-200 px-3 py-1 text-sm font-medium capitalize text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
            {scan.status}
          </span>
        </header>

        <div className="space-y-5 sm:space-y-6">
          <ScanProgressBar status={scan.status} />
          {scan.status === "done" ? (
            <VerdictBanner verdict={scan.verdict} />
          ) : (
            <section
              aria-label="Awaiting verdict"
              className="flex min-h-28 items-center justify-center rounded-xl border border-zinc-200 bg-white p-5 text-sm font-medium text-zinc-500 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400 sm:p-6"
            >
              Awaiting verdict...
            </section>
          )}

          <div className="grid grid-cols-1 items-stretch gap-5 sm:gap-6 lg:grid-cols-2">
            <ClaimsCard claims={scan.claims} />
            <BehaviorTimeline events={scan.events} />
          </div>
        </div>
      </div>
    </main>
  );
}
