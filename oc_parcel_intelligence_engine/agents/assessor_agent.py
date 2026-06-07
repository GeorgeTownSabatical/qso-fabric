"""Assessor lookup agent."""

from __future__ import annotations

from core.oc_clients import MockAssessorClient


class AssessorAgent:
    def __init__(self):
        self.client = MockAssessorClient()

    def lookup(self, apn: str) -> dict:
        return self.client.lookup(apn)
