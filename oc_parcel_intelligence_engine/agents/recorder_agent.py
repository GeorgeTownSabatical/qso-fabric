"""Recorder document lookup agent."""

from __future__ import annotations

from core.oc_clients import MockRecorderClient


class RecorderAgent:
    def __init__(self):
        self.client = MockRecorderClient()

    def fetch_documents(self, apn: str) -> list[dict]:
        return self.client.fetch_documents(apn)
