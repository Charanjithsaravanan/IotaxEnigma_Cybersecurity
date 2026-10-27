"""PkgGuard AI and semantic analysis engine."""

from .analyzer import (
    BehavioralFingerprint,
    ClaimedIntent,
    ScanVerdict,
    evaluate_mismatch,
    extract_claimed_intent,
)

__all__ = [
    "BehavioralFingerprint",
    "ClaimedIntent",
    "ScanVerdict",
    "evaluate_mismatch",
    "extract_claimed_intent",
]
