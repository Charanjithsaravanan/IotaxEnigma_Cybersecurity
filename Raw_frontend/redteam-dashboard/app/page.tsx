"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  FileCode2,
  FileText,
  GitBranch,
  History,
  LockKeyhole,
  Play,
  ShieldAlert,
  ShieldCheck,
  Upload,
  Zap,
} from "lucide-react";
import { createLocalScan, executeSandboxScan, seedExampleScans } from "../lib/localScans";
import { supabase } from "../lib/supabaseClient";
import { mockScans } from "../lib/mockScans";
import type { Scan } from "../types/scan";

const examples = [
  {
    id: "clean-left-pad",
    label: "Clean utility",
    description: "A harmless string helper with no external access.",
    icon: ShieldCheck,
    tone: "text-emerald-300 bg-emerald-400/10 border-emerald-300/20",
  },
  {
    id: "http-fetcher",
    label: "Expected network",
    description: "An HTTP client whose network behavior matches its README.",
    icon: Zap,
    tone: "text-sky-300 bg-sky-400/10 border-sky-300/20",
  },
  {
    id: "evil-left-pad",
    label: "Credential theft",
    description: "A string utility that reaches for SSH keys and curl.",
    icon: ShieldAlert,
    tone: "text-rose-300 bg-rose-400/10 border-rose-300/20",
  },
];

export default function Home() {
  const router = useRouter();
  const [packageName, setPackageName] = useState("");
  const [readme, setReadme] = useState("");
  const [source, setSource] = useState("");
  const [activeTab, setActiveTab] = useState<"paste" | "examples">("paste");
  const [recentScans] = useState<Scan[]>(mockScans);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    seedExampleScans(mockScans);
  }, []);

  function loadExample(id: string) {
    const example = mockScans.find((scan) => scan.id === id);
    if (!example) return;

    setPackageName(example.package_name);
    setReadme(example.claims.summary);
    setSource(
      example.events.length > 0
        ? example.events.map((event) => event.detail).join("\n")
        : "def pad(value, width):\n    return value.rjust(width)",
    );
    setActiveTab("paste");
  }

  function submitScan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    void (async () => {
      try {
        const remoteScan = await executeSandboxScan(
          { packageName, readme, source },
          (await supabase?.auth.getSession())?.data.session?.access_token,
        );
        const scan = remoteScan ?? createLocalScan({ packageName, readme, source });
        router.push(`/scan/${scan.id}`);
      } catch (error) {
        setIsSubmitting(false);
        window.alert(error instanceof Error ? error.message : "The scan failed.");
      }
    })();
  }

  return (
    <main className="min-h-screen bg-[#07111f] text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_8%_0%,rgba(45,212,191,0.14),transparent_28%),radial-gradient(circle_at_92%_30%,rgba(59,130,246,0.12),transparent_30%)]" />
      <div className="relative mx-auto max-w-7xl px-5 py-5 sm:px-8 lg:px-12">
        <header className="flex items-center justify-between border-b border-white/10 pb-5">
          <Link className="flex items-center gap-3" href="/">
            <span className="flex size-10 items-center justify-center rounded-xl border border-teal-300/20 bg-teal-300/10 text-teal-300">
              <ShieldCheck className="size-5" />
            </span>
            <span className="text-sm font-semibold tracking-[0.18em] uppercase">
              Traceguard
            </span>
          </Link>
          <div className="flex items-center gap-3">
            <span className="hidden text-xs text-slate-500 sm:inline">
              Local demo workspace
            </span>
            <Link
              className="rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-300 transition hover:border-teal-300/40 hover:text-white"
              href="/login"
            >
              Sign in
            </Link>
          </div>
        </header>

        <section className="grid gap-12 py-14 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-20">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-teal-300/20 bg-teal-300/10 px-3 py-1.5 text-xs font-medium text-teal-200">
              <span className="size-1.5 rounded-full bg-teal-300 shadow-[0_0_10px_rgba(45,212,191,0.8)]" />
              Behavioral supply-chain intelligence
            </div>
            <h1 className="max-w-3xl text-4xl font-semibold leading-[1.05] tracking-tight text-balance sm:text-6xl">
              See what a package does
              <span className="block text-teal-300">before you trust it.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-400">
              Paste a README and package source. Traceguard compares the
              package&apos;s claims with install and import behavior, then
              gives your team evidence instead of signatures.
            </p>
            <div className="mt-8 flex flex-wrap gap-5 text-sm text-slate-300">
              {["Install-time traces", "Import-time traces", "Evidence-backed verdicts"].map(
                (item) => (
                  <span className="flex items-center gap-2" key={item}>
                    <CheckCircle2 className="size-4 text-teal-300" />
                    {item}
                  </span>
                ),
              )}
            </div>
          </div>

          <section className="rounded-3xl border border-white/10 bg-white/[0.07] p-5 shadow-2xl shadow-black/30 backdrop-blur-xl sm:p-7">
            <div className="mb-6 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-teal-300">
                  New analysis
                </p>
                <h2 className="mt-2 text-2xl font-semibold">Fingerprint a package</h2>
              </div>
              <span className="rounded-lg border border-white/10 bg-black/10 p-2 text-slate-400">
                <LockKeyhole className="size-4" />
              </span>
            </div>

            <div className="mb-5 grid grid-cols-2 rounded-xl border border-white/10 bg-black/10 p-1">
              <button
                className={`rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  activeTab === "paste" ? "bg-white text-slate-950" : "text-slate-400 hover:text-white"
                }`}
                onClick={() => setActiveTab("paste")}
                type="button"
              >
                Paste package
              </button>
              <button
                className={`rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  activeTab === "examples" ? "bg-white text-slate-950" : "text-slate-400 hover:text-white"
                }`}
                onClick={() => setActiveTab("examples")}
                type="button"
              >
                Try a case
              </button>
            </div>

            {activeTab === "examples" ? (
              <div className="space-y-3">
                {examples.map((example) => {
                  const Icon = example.icon;
                  return (
                    <button
                      className="flex w-full items-center gap-3 rounded-xl border border-white/10 bg-black/10 p-3 text-left transition hover:border-teal-300/30 hover:bg-white/[0.06]"
                      key={example.id}
                      onClick={() => loadExample(example.id)}
                      type="button"
                    >
                      <span className={`flex size-10 shrink-0 items-center justify-center rounded-lg border ${example.tone}`}>
                        <Icon className="size-5" />
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-medium text-white">{example.label}</span>
                        <span className="mt-0.5 block text-xs leading-5 text-slate-400">{example.description}</span>
                      </span>
                      <ArrowRight className="ml-auto size-4 shrink-0 text-slate-500" />
                    </button>
                  );
                })}
              </div>
            ) : (
              <form className="space-y-4" onSubmit={submitScan}>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-slate-200">Package name</span>
                  <input
                    className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-teal-300/60 focus:ring-2 focus:ring-teal-300/10"
                    onChange={(event) => setPackageName(event.target.value)}
                    placeholder="e.g. clean-left-pad"
                    required
                    value={packageName}
                  />
                </label>
                <label className="block">
                  <span className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-200">
                    <FileText className="size-4 text-slate-400" /> README or metadata
                  </span>
                  <textarea
                    className="min-h-24 w-full resize-y rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-teal-300/60 focus:ring-2 focus:ring-teal-300/10"
                    onChange={(event) => setReadme(event.target.value)}
                    placeholder="What does this package claim to do?"
                    required
                    value={readme}
                  />
                </label>
                <label className="block">
                  <span className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-200">
                    <FileCode2 className="size-4 text-slate-400" /> Package source or trace notes
                  </span>
                  <textarea
                    className="min-h-28 w-full resize-y rounded-xl border border-white/10 bg-black/20 px-4 py-3 font-mono text-xs leading-5 text-white outline-none placeholder:text-slate-600 focus:border-teal-300/60 focus:ring-2 focus:ring-teal-300/10"
                    onChange={(event) => setSource(event.target.value)}
                    placeholder="Paste a small source file, setup.py, package.json, or observed trace..."
                    required
                    value={source}
                  />
                </label>
                <button
                  className="group flex w-full items-center justify-center gap-2 rounded-xl bg-teal-300 px-4 py-3.5 text-sm font-semibold text-slate-950 transition hover:bg-teal-200 disabled:cursor-wait disabled:opacity-70"
                  disabled={isSubmitting}
                  type="submit"
                >
                  {isSubmitting ? "Preparing analysis..." : "Run behavioral fingerprint"}
                  <Play className="size-4 transition group-hover:translate-x-0.5" />
                </button>
                <p className="flex items-center justify-center gap-2 text-center text-xs text-slate-500">
                  <Upload className="size-3.5" /> Demo mode stores scans only in this browser
                </p>
              </form>
            )}
          </section>
        </section>

        <section className="border-t border-white/10 py-10">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
                <History className="size-3.5" /> Recent cases
              </p>
              <h2 className="mt-2 text-xl font-semibold">Behavior library</h2>
            </div>
            <span className="text-xs text-slate-500">{recentScans.length} seeded examples</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            {recentScans.map((scan) => (
              <Link
                className="group rounded-2xl border border-white/10 bg-white/[0.04] p-4 transition hover:-translate-y-0.5 hover:border-teal-300/30 hover:bg-white/[0.07]"
                href={`/scan/${encodeURIComponent(scan.id)}`}
                key={scan.id}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate text-sm font-semibold text-white">{scan.package_name}</span>
                  <span className={`size-2 rounded-full ${scan.verdict.risk === "high" ? "bg-rose-400" : scan.verdict.risk === "medium" ? "bg-amber-400" : "bg-emerald-400"}`} />
                </div>
                <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-400">{scan.claims.summary}</p>
                <div className="mt-4 flex items-center justify-between text-xs">
                  <span className="text-slate-500">{scan.events.length} observed events</span>
                  <span className="font-semibold text-slate-300">{scan.verdict.score}/100</span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 py-6 text-xs text-slate-500">
          <span>Traceguard · Behavioral package intelligence</span>
          <span className="flex items-center gap-2"><GitBranch className="size-3.5" /> npm + PyPI ready</span>
        </footer>
      </div>
    </main>
  );
}
