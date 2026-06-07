"""HTTP client wrapper for RecorderWorks acquisition."""

from __future__ import annotations

from pathlib import Path
import os
import time

from acquire.slicer import QuerySlice, hash_slice


class RecorderClient:
    def __init__(self, *, base_url: str | None = None, post_path: str | None = None, timeout: int | None = None):
        self.base_url = base_url or os.getenv("OCRECORDER_BASE_URL", "https://cr.occlerkrecorder.gov/RecorderWorksInternet/")
        self.post_path = post_path if post_path is not None else os.getenv("OCRECORDER_POST_PATH", "")
        self.timeout = int(timeout or os.getenv("OCRECORDER_TIMEOUT", "30"))
        self.sleep_seconds = float(os.getenv("OCRECORDER_SLEEP_SECONDS", "0.75"))
        self._session = None

    def _get_session(self):
        if self._session is None:
            try:
                import requests
            except ImportError as exc:
                raise RuntimeError("requests is required for acquisition. Install with: pip install 'ocrecorder-pipeline[acquire]'") from exc
            self._session = requests.Session()
        return self._session

    def search(self, q: QuerySlice) -> str:
        session = self._get_session()
        payload = {
            "grantorGrantee": q.surname,
            "recordingDateFrom": q.date_from,
            "recordingDateTo": q.date_to,
            "documentType": q.doc_type or "",
            "page": q.page,
        }
        url = self.base_url.rstrip("/") + "/" + self.post_path.lstrip("/") if self.post_path else self.base_url
        resp = session.post(url, data=payload, timeout=self.timeout)
        resp.raise_for_status()
        if self.sleep_seconds > 0:
            time.sleep(self.sleep_seconds)
        return resp.text


def save_raw(outdir: Path, q: QuerySlice, html: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    filename = f"{q.surname}_{q.date_from}_{q.date_to}_{q.page}_{hash_slice(q)}.html"
    path = outdir / filename
    path.write_text(html, encoding="utf-8")
    return path
