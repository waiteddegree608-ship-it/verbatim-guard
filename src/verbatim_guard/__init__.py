"""Deterministic quotation checks. Matching text is not proof that a claim is true."""
from .core import Match, Result, fingerprint, verify
from .bundle import check_bundle

__all__ = ["Match", "Result", "fingerprint", "verify", "check_bundle"]
__version__ = "0.1.0"
