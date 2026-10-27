"""Claim extraction and behavioral risk scoring for PkgGuard."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .prompts import (
    FORENSIC_VERDICT_SYSTEM_PROMPT,
    INTENT_EXTRACTION_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class ClaimedIntent(BaseModel):
    """Capabilities a package documents or reasonably requires."""

    model_config = ConfigDict(extra="ignore")

    package_name: str = ""
    summary: str = ""
    expects_network: bool = False
    expects_file_read_outside_pkg: bool = False
    expects_subprocess: bool = False
    expects_env_reads: list[str] = Field(default_factory=list)
    has_install_script: bool = False


TraceValue = str | dict[str, Any]


class BehaviorTrace(BaseModel):
    """Observed actions during one package lifecycle phase."""

    model_config = ConfigDict(extra="ignore")

    network_calls: list[TraceValue] = Field(default_factory=list)
    files_touched: list[TraceValue] = Field(default_factory=list)
    env_vars_read: list[TraceValue] = Field(default_factory=list)
    subprocesses_spawned: list[TraceValue] = Field(default_factory=list)


class BehavioralFingerprint(BaseModel):
    """The install/import traces emitted by the sandbox."""

    model_config = ConfigDict(extra="ignore")

    install_time: BehaviorTrace = Field(default_factory=BehaviorTrace)
    import_time: BehaviorTrace = Field(default_factory=BehaviorTrace)


class ScanVerdict(BaseModel):
    """Final risk assessment returned to the backend."""

    model_config = ConfigDict(extra="ignore")

    risk_score: int = Field(ge=0, le=100)
    severity: Literal["low", "medium", "high", "critical"]
    explanation: str
    findings: list[str] = Field(default_factory=list)


class _SemanticAssessment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    risk_score: int = Field(ge=0, le=100)
    llm_explanation: str
    findings: list[str] = Field(default_factory=list)


_STANDARD_ENV_VARS = {
    "PATH",
    "HOME",
    "LANG",
    "PYTHONPATH",
    "NODE_ENV",
}
_STANDARD_PATH_PREFIXES = ("/usr/lib", "/lib")
_SECRET_ENV_PREFIXES = ("AWS_", "GITHUB_")
def _make_chain() -> Any | None:
    """Create the configured LangChain structured-output chain, if enabled."""
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    ollama_model = os.getenv("OLLAMA_MODEL")
    if not gemini_api_key and not ollama_model:
        return None

    try:
        if gemini_api_key:
            from langchain_google_genai import ChatGoogleGenerativeAI

            model = ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
                google_api_key=gemini_api_key,
            )
        else:
            from langchain_ollama import ChatOllama

            model = ChatOllama(model=ollama_model)
        return model
    except (ImportError, ValueError) as error:
        logger.warning("LLM provider is configured but unavailable: %s", error)
        return None


def _invoke_structured(
    schema: type[BaseModel],
    system_prompt: str,
    human_prompt: str,
) -> BaseModel | None:
    model = _make_chain()
    if model is None:
        return None
    try:
        from langchain_core.prompts import ChatPromptTemplate

        chain = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", "{input}")]
        ) | model.with_structured_output(schema)
        result = chain.invoke({"input": human_prompt})
        return result if isinstance(result, schema) else schema.model_validate(result)
    except Exception as error:
        logger.warning("Structured LLM analysis failed; using local fallback: %s", error)
        return None


def _heuristic_intent(readme_text: str, metadata: dict[str, Any]) -> ClaimedIntent:
    text = f"{readme_text}\n{metadata}".lower()
    expects_network = any(
        term in text
        for term in (
            "http request",
            "http client",
            "api client",
            "web scraping",
            "database driver",
            "cloud sdk",
            "telemetry",
            "remote asset",
        )
    )
    expects_file_read = any(
        term in text
        for term in (
            "local file",
            "local configuration",
            "configuration file",
            "read user files",
            "write user files",
            "filesystem",
            "system logs",
        )
    )
    expects_subprocess = any(
        term in text
        for term in ("wraps ffmpeg", "wraps git", "compiler tool", "task runner")
    )
    env_matches = re.findall(
        r"\b[A-Z][A-Z0-9_]*(?:_API_KEY|_KEY|_TOKEN|_URL|_SECRET|_HOST|_PORT|_DEBUG)\b",
        readme_text or "",
        flags=re.IGNORECASE,
    )
    expects_env_reads = sorted({match.upper() for match in env_matches})
    name = str(metadata.get("name") or metadata.get("project_name") or "")
    summary = str(metadata.get("description") or metadata.get("summary") or "")
    return ClaimedIntent(
        package_name=name,
        summary=summary,
        expects_network=expects_network,
        expects_file_read_outside_pkg=expects_file_read,
        expects_subprocess=expects_subprocess,
        expects_env_reads=expects_env_reads,
        has_install_script=bool(
            metadata.get("scripts")
            and any(
                key in metadata["scripts"]
                for key in ("preinstall", "install", "postinstall")
            )
        ),
    )


def extract_claimed_intent(readme_text: str, metadata: dict) -> ClaimedIntent:
    """Extract documented capabilities with a structured LLM or local fallback."""
    metadata_text = repr(metadata)
    result = _invoke_structured(
        ClaimedIntent,
        INTENT_EXTRACTION_SYSTEM_PROMPT,
        f"Package metadata:\n{metadata_text}\n\nREADME:\n{readme_text}",
    )
    if isinstance(result, ClaimedIntent):
        return result
    return _heuristic_intent(readme_text, metadata)


def _entry_text(value: TraceValue) -> str:
    if isinstance(value, str):
        return value
    return " ".join(str(part) for part in value.values())


def _env_name(value: TraceValue) -> str:
    if isinstance(value, dict):
        for key in ("name", "variable", "env_var", "key"):
            if key in value:
                return str(value[key])
    return _entry_text(value)


def _path_text(value: TraceValue) -> str:
    if isinstance(value, dict):
        for key in ("path", "file", "filename", "target"):
            if key in value:
                return str(value[key])
    return _entry_text(value)


def _is_standard_library_path(value: TraceValue) -> bool:
    path = _path_text(value).replace("\\", "/").lower()
    return (
        any(path == prefix or path.startswith(prefix + "/") for prefix in _STANDARD_PATH_PREFIXES)
        or "site-packages" in path
    )


def _filtered_trace(trace: BehaviorTrace) -> BehaviorTrace:
    filtered = trace.model_copy(deep=True)
    filtered.env_vars_read = [
        value
        for value in trace.env_vars_read
        if _env_name(value).strip().upper() not in _STANDARD_ENV_VARS
    ]
    filtered.files_touched = [
        value
        for value in trace.files_touched
        if not _is_standard_library_path(value)
    ]
    return filtered


def _strings(values: list[TraceValue]) -> list[str]:
    return [_entry_text(value) for value in values]


def _score_behavior(
    claimed: ClaimedIntent, actual: BehavioralFingerprint
) -> tuple[int, list[str]]:
    install = _filtered_trace(actual.install_time)
    imported = _filtered_trace(actual.import_time)
    findings: list[str] = []
    score = 0

    if install.network_calls:
        score += 55
        findings.append("The package made network calls during installation.")
    if imported.network_calls and not claimed.expects_network:
        score += 25
        findings.append("Import-time network activity is not documented.")

    all_files = _strings(install.files_touched + imported.files_touched)
    sensitive_path = re.compile(
        r"(?:^|[/\\])(?:\.ssh|\.aws|\.config[/\\]gcloud)(?:[/\\]|$)", re.I
    )
    if any(sensitive_path.search(path) for path in all_files):
        score += 90
        findings.append("The package touched a sensitive credential directory.")

    expected_env = {value.upper() for value in claimed.expects_env_reads}
    secret_reads = [
        _env_name(value).strip()
        for value in install.env_vars_read + imported.env_vars_read
        if any(
            _env_name(value).strip().upper().startswith(prefix)
            for prefix in _SECRET_ENV_PREFIXES
        )
        and _env_name(value).strip().upper() not in expected_env
    ]
    if secret_reads:
        score += 80
        findings.append("The package read undeclared AWS or GitHub environment variables.")

    if install.subprocesses_spawned:
        score += 40
        findings.append("The package spawned a subprocess during installation.")
    if imported.subprocesses_spawned and not claimed.expects_subprocess:
        score += 25
        findings.append("Import-time subprocess activity is not documented.")

    if imported.files_touched and not claimed.expects_file_read_outside_pkg:
        score += 10
        findings.append("Import-time filesystem access is not documented.")

    return min(score, 100), findings


def _severity(score: int) -> Literal["low", "medium", "high", "critical"]:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def evaluate_mismatch(
    claimed: ClaimedIntent, actual: BehavioralFingerprint
) -> ScanVerdict:
    """Score observed behavior deterministically, then optionally refine its explanation."""
    actual = (
        actual
        if isinstance(actual, BehavioralFingerprint)
        else BehavioralFingerprint.model_validate(actual)
    )
    base_score, findings = _score_behavior(claimed, actual)
    assessment = _invoke_structured(
        _SemanticAssessment,
        FORENSIC_VERDICT_SYSTEM_PROMPT,
        (
            f"Documented intent:\n{claimed.model_dump_json(indent=2)}\n\n"
            f"Observed behavior:\n{actual.model_dump_json(indent=2)}\n\n"
            f"deterministic_flags (risk score lower bound {base_score}): {findings}"
        ),
    )

    score = base_score
    explanation = " ".join(findings) if findings else (
        "Observed behavior is consistent with the documented capabilities."
    )
    if isinstance(assessment, _SemanticAssessment):
        score = max(base_score, assessment.risk_score)
        explanation = assessment.llm_explanation or explanation
        findings = list(dict.fromkeys(findings + assessment.findings))

    return ScanVerdict(
        risk_score=score,
        severity=_severity(score),
        explanation=explanation,
        findings=findings,
    )
