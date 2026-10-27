# shared/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

class PhaseTrace(BaseModel):
    network_calls: List[str] = Field(default_factory=list)
    files_touched: List[str] = Field(default_factory=list)
    env_vars_read: List[str] = Field(default_factory=list)
    subprocesses_spawned: List[str] = Field(default_factory=list)

class BehavioralFingerprint(BaseModel):
    install_time: PhaseTrace = Field(default_factory=PhaseTrace)
    import_time: PhaseTrace = Field(default_factory=PhaseTrace)

class ClaimedIntent(BaseModel):
    summary: str = "No description provided."
    expects_network: bool = False
    expects_file_read_outside_pkg: bool = False
    expects_subprocess: bool = False
    expects_env_reads: List[str] = Field(default_factory=list)

class ScanVerdict(BaseModel):
    risk_score: int
    verdict: str  # "safe" | "suspicious" | "malicious"
    mismatch_flags: List[str]
    llm_explanation: str

class ScanRequest(BaseModel):
    ecosystem: str = "pypi"  # "pypi" or "npm"
    name: str
    version: str = "latest"
    force_rescan: bool = False

class LocalScanRequest(BaseModel):
    ecosystem: str = "pypi"
    name: str = Field(min_length=1, max_length=128)
    readme: str = Field(min_length=1, max_length=100_000)
    source: str = Field(min_length=1, max_length=500_000)
