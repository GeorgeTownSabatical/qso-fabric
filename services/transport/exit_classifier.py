from __future__ import annotations

from typing import Any


class ExitClassifier:
    """Simple deterministic risk classifier for Tor exits."""

    _HIGH_RISK_COUNTRIES = {"RU", "IR", "KP", "SY"}
    _ELEVATED_RISK_ASNS = {"AS12389", "AS14061", "AS202425"}

    def classify(
        self,
        *,
        exit_ip: str,
        country_code: str = "",
        asn: str = "",
        abuse_score: float = 0.0,
    ) -> dict[str, Any]:
        score = 0
        normalized_country = country_code.upper().strip()
        normalized_asn = asn.upper().strip()

        if normalized_country in self._HIGH_RISK_COUNTRIES:
            score += 3
        if normalized_asn in self._ELEVATED_RISK_ASNS:
            score += 2
        if abuse_score >= 0.8:
            score += 3
        elif abuse_score >= 0.5:
            score += 2
        elif abuse_score > 0:
            score += 1

        if score >= 6:
            category = "high"
        elif score >= 3:
            category = "medium"
        else:
            category = "low"

        return {
            "exit_ip": str(exit_ip),
            "country_code": normalized_country,
            "asn": normalized_asn,
            "abuse_score": float(abuse_score),
            "risk_score": score,
            "risk_category": category,
        }
