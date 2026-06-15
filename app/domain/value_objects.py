from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.core.exceptions import UnprocessableEntityException

_RUT_CLEAN_RE = re.compile(r"[.\s-]")


@dataclass(frozen=True)
class Rut:
    """A Chilean national ID (RUT) as a validated, normalized value.

    Centralizes the modulo-11 check-digit rule that previously lived only in the
    seed. Construct via :meth:`parse` for untrusted input, or
    :meth:`deterministic_for` to derive a stable well-formed RUT from an email
    (used by the seed/backfill so re-runs are idempotent).
    """

    body: int
    check_digit: str

    @staticmethod
    def compute_check_digit(body: int) -> str:
        # Standard Chilean RUT verifier digit (modulo 11).
        total = 0
        factor = 2
        for digit in reversed(str(body)):
            total += int(digit) * factor
            factor = 2 if factor == 7 else factor + 1
        remainder = 11 - (total % 11)
        if remainder == 11:
            return "0"
        if remainder == 10:
            return "K"
        return str(remainder)

    @classmethod
    def parse(cls, raw: str) -> "Rut":
        cleaned = _RUT_CLEAN_RE.sub("", (raw or "").strip()).upper()
        if len(cleaned) < 2 or not cleaned[:-1].isdigit():
            raise UnprocessableEntityException("Invalid RUT")
        body, check_digit = int(cleaned[:-1]), cleaned[-1]
        if cls.compute_check_digit(body) != check_digit:
            raise UnprocessableEntityException("Invalid RUT")
        return cls(body=body, check_digit=check_digit)

    @classmethod
    def deterministic_for(cls, email: str) -> "Rut":
        # Deterministic 8-digit body derived from the email so the seed/backfill
        # always yields the same value for a given member without a random() that
        # would drift between runs.
        body = 10_000_000 + (int(hashlib.md5(email.encode()).hexdigest()[:8], 16) % 15_000_000)
        return cls(body=body, check_digit=cls.compute_check_digit(body))

    def __str__(self) -> str:
        return f"{self.body}-{self.check_digit}"
