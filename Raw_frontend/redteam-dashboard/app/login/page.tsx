"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import {
  ArrowRight,
  Check,
  Code2,
  Eye,
  EyeOff,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { supabase } from "../../lib/supabaseClient";

type AuthMode = "sign-in" | "sign-up";

const benefits = [
  "Run behavioral fingerprints in isolated sandboxes",
  "Compare runtime behavior with package claims",
  "Share clear, evidence-backed verdicts with your team",
];

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("sign-in");
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void (async () => {
      if (supabase) {
        const result =
          mode === "sign-in"
            ? await supabase.auth.signInWithPassword({ email, password })
            : await supabase.auth.signUp({ email, password });
        if (result.error) {
          setNotice(result.error.message);
          return;
        }
        setNotice(
          mode === "sign-in"
            ? "Signed in. Opening your workspace..."
            : result.data.session
              ? "Workspace created. Opening your dashboard..."
              : "Check your email to confirm your account, then sign in.",
        );
        if (result.data.session) window.setTimeout(() => router.push("/"), 450);
        return;
      }

      window.localStorage.setItem(
        "traceguard:session",
        JSON.stringify({ email, signedInAt: new Date().toISOString() }),
      );
      setNotice("Demo sign-in successful. Opening your workspace...");
      window.setTimeout(() => router.push("/"), 450);
    })();
  }

  function handleOAuth(provider: string) {
    if (supabase) {
      void supabase.auth.signInWithOAuth({
        provider: provider.toLowerCase() as "google" | "github",
        options: { redirectTo: `${window.location.origin}/` },
      });
      return;
    }
    window.localStorage.setItem(
      "traceguard:session",
      JSON.stringify({ provider, signedInAt: new Date().toISOString() }),
    );
    setNotice(`${provider} demo sign-in successful. Opening your workspace...`);
    window.setTimeout(() => router.push("/"), 450);
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#07111f] text-white">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_10%,rgba(45,212,191,0.16),transparent_30%),radial-gradient(circle_at_88%_85%,rgba(59,130,246,0.18),transparent_35%)]" />
      <div className="pointer-events-none absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(148,163,184,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.08)_1px,transparent_1px)] [background-size:48px_48px]" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-7xl flex-col px-5 py-5 sm:px-8 lg:px-12">
        <header className="flex items-center justify-between">
          <Link className="group flex items-center gap-3" href="/">
            <span className="flex size-10 items-center justify-center rounded-xl border border-teal-300/20 bg-teal-300/10 text-teal-300 shadow-[0_0_24px_rgba(45,212,191,0.14)] transition group-hover:bg-teal-300/20">
              <ShieldCheck className="size-5" />
            </span>
            <span className="text-sm font-semibold tracking-[0.18em] text-slate-100 uppercase">
              Traceguard
            </span>
          </Link>
          <Link
            className="text-sm text-slate-400 transition hover:text-white"
            href="/"
          >
            Back to scans <ArrowRight className="ml-1 inline size-4" />
          </Link>
        </header>

        <div className="grid flex-1 items-center gap-12 py-12 lg:grid-cols-[1fr_480px] lg:gap-20 lg:py-16">
          <section className="hidden max-w-xl lg:block">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-teal-300/20 bg-teal-300/10 px-3 py-1.5 text-xs font-medium text-teal-200">
              <Sparkles className="size-3.5" />
              Trust what your dependencies do
            </div>
            <h1 className="text-5xl font-semibold leading-[1.08] tracking-tight text-balance xl:text-6xl">
              Know what ships
              <span className="block text-teal-300">before it runs.</span>
            </h1>
            <p className="mt-6 max-w-lg text-lg leading-8 text-slate-400">
              Traceguard turns install-time and import-time behavior into
              evidence your team can act on — not just another list of
              signatures.
            </p>
            <ul className="mt-9 space-y-4">
              {benefits.map((benefit) => (
                <li className="flex items-center gap-3 text-sm text-slate-300" key={benefit}>
                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-teal-300/10 text-teal-300">
                    <Check className="size-3.5" />
                  </span>
                  {benefit}
                </li>
              ))}
            </ul>
            <div className="mt-12 flex items-center gap-3 text-xs text-slate-500">
              <span className="size-2 rounded-full bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.8)]" />
              Sandboxed analysis pipeline ready
            </div>
          </section>

          <section className="animate-fade-in-up rounded-3xl border border-white/10 bg-white/[0.07] p-6 shadow-2xl shadow-black/30 backdrop-blur-xl sm:p-8">
            <div className="mb-8 lg:hidden">
              <p className="text-sm font-medium text-teal-300">TRACEGUARD</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight">
                Secure your package decisions.
              </h1>
            </div>
            <div className="mb-8">
              <div className="mb-2 flex items-center gap-2 text-slate-400">
                <LockKeyhole className="size-4" />
                <span className="text-xs font-medium uppercase tracking-[0.16em]">
                  Private workspace
                </span>
              </div>
              <h2 className="text-2xl font-semibold tracking-tight">
                {mode === "sign-in" ? "Welcome back" : "Create your workspace"}
              </h2>
              <p className="mt-2 text-sm text-slate-400">
                {mode === "sign-in"
                  ? "Sign in to review your package intelligence."
                  : "Start building a safer dependency pipeline."}
              </p>
            </div>

            <div className="mb-6 grid grid-cols-2 rounded-xl border border-white/10 bg-black/10 p-1">
              {(["sign-in", "sign-up"] as const).map((nextMode) => (
                <button
                  className={`rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    mode === nextMode
                      ? "bg-white text-slate-950 shadow-sm"
                      : "text-slate-400 hover:text-white"
                  }`}
                  key={nextMode}
                  onClick={() => {
                    setMode(nextMode);
                    setNotice("");
                  }}
                  type="button"
                >
                  {nextMode === "sign-in" ? "Sign in" : "Create account"}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.06] px-3 py-3 text-sm font-medium text-slate-200 transition hover:border-white/20 hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-300"
                onClick={() => handleOAuth("Google")}
                type="button"
              >
                <span className="flex size-5 items-center justify-center rounded-full bg-white text-xs font-bold text-[#4285f4]">
                  G
                </span>
                Google
              </button>
              <button
                className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.06] px-3 py-3 text-sm font-medium text-slate-200 transition hover:border-white/20 hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-300"
                onClick={() => handleOAuth("GitHub")}
                type="button"
              >
                <Code2 className="size-4" />
                GitHub
              </button>
            </div>

            <div className="my-6 flex items-center gap-3 text-xs text-slate-500">
              <span className="h-px flex-1 bg-white/10" />
              or continue with email
              <span className="h-px flex-1 bg-white/10" />
            </div>

            <form className="space-y-4" onSubmit={handleSubmit}>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-200">
                  Work email
                </span>
                <input
                  autoComplete="email"
                  className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-teal-300/70 focus:ring-2 focus:ring-teal-300/15"
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@company.com"
                  required
                  type="email"
                  value={email}
                />
              </label>
              <label className="block">
                <span className="mb-2 block text-sm font-medium text-slate-200">
                  Password
                </span>
                <span className="relative block">
                  <input
                    autoComplete={mode === "sign-in" ? "current-password" : "new-password"}
                    className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 pr-12 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-teal-300/70 focus:ring-2 focus:ring-teal-300/15"
                    minLength={8}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder="At least 8 characters"
                    required
                    type={showPassword ? "text" : "password"}
                    value={password}
                  />
                  <button
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-500 transition hover:text-slate-200 focus-visible:outline-2 focus-visible:outline-teal-300"
                    onClick={() => setShowPassword((visible) => !visible)}
                    type="button"
                  >
                    {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </span>
              </label>

              {mode === "sign-in" && (
                <div className="flex justify-end">
                  <button
                    className="text-xs font-medium text-teal-300 transition hover:text-teal-200"
                    onClick={() =>
                      setNotice("Password reset will be enabled when the backend email route is connected.")
                    }
                    type="button"
                  >
                    Forgot password?
                  </button>
                </div>
              )}

              <button
                className="group flex w-full items-center justify-center gap-2 rounded-xl bg-teal-300 px-4 py-3.5 text-sm font-semibold text-slate-950 transition hover:bg-teal-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-200"
                type="submit"
              >
                {mode === "sign-in" ? "Sign in to Traceguard" : "Create workspace"}
                <ArrowRight className="size-4 transition group-hover:translate-x-0.5" />
              </button>
            </form>

            {notice && (
              <p
                aria-live="polite"
                className="mt-4 rounded-lg border border-teal-300/20 bg-teal-300/10 px-3 py-2.5 text-xs leading-5 text-teal-100"
              >
                {notice}
              </p>
            )}

            <p className="mt-6 text-center text-xs leading-5 text-slate-500">
              By continuing, you agree to Traceguard&apos;s Terms and Privacy
              Policy.
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
