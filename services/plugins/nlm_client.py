from __future__ import annotations

import copy
import time
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class NLMDigitalCollectionsRateLimitError(RuntimeError):
    """Raised when local request pacing would exceed NLM's published limit."""


class NLMDigitalCollectionsClientError(RuntimeError):
    """Raised when NLM responses are unavailable or malformed."""


@dataclass
class _CacheEntry:
    created_at: float
    payload: Dict[str, Any]


class NLMDigitalCollectionsClient:
    BASE_URL = "https://wsearch.nlm.nih.gov/ws/query"
    MAX_REQUESTS_PER_MINUTE = 85
    DEFAULT_CACHE_TTL_SECONDS = 12 * 60 * 60

    def __init__(self, *, tool: str = "qso_fabric_demo", email: str | None = None) -> None:
        self.tool = tool
        self.email = email
        self._request_times: deque[float] = deque()
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = Lock()

    def search(
        self,
        *,
        term: str,
        retmax: int = 10,
        tool: str | None = None,
        email: str | None = None,
        use_cache: bool = True,
        cache_ttl_seconds: int | None = None,
    ) -> Dict[str, Any]:
        query = str(term).strip()
        if not query:
            raise ValueError("term is required")

        params: dict[str, Any] = {
            "db": "digitalCollections",
            "term": query,
            "retmax": self._clamp_retmax(retmax),
        }
        self._attach_client_params(params=params, tool=tool, email=email)
        return self._query(params=params, use_cache=use_cache, cache_ttl_seconds=cache_ttl_seconds)

    def continue_search(
        self,
        *,
        file: str,
        server: str,
        retstart: int,
        retmax: int = 10,
        tool: str | None = None,
        email: str | None = None,
        use_cache: bool = True,
        cache_ttl_seconds: int | None = None,
    ) -> Dict[str, Any]:
        file_id = str(file).strip()
        server_name = str(server).strip()
        if not file_id:
            raise ValueError("file is required")
        if not server_name:
            raise ValueError("server is required")

        start = int(retstart)
        if start < 0:
            raise ValueError("retstart must be a non-negative integer")

        params: dict[str, Any] = {
            "file": file_id,
            "server": server_name,
            "retstart": start,
            "retmax": self._clamp_retmax(retmax),
        }
        self._attach_client_params(params=params, tool=tool, email=email)
        return self._query(params=params, use_cache=use_cache, cache_ttl_seconds=cache_ttl_seconds)

    def _attach_client_params(self, *, params: dict[str, Any], tool: str | None, email: str | None) -> None:
        effective_tool = str(tool).strip() if tool is not None else str(self.tool).strip()
        effective_email = str(email).strip() if email is not None else str(self.email or "").strip()
        if effective_tool:
            params["tool"] = effective_tool
        if effective_email:
            params["email"] = effective_email

    def _clamp_retmax(self, retmax: int) -> int:
        value = int(retmax)
        if value < 1:
            return 1
        if value > 200:
            return 200
        return value

    def _query(self, *, params: dict[str, Any], use_cache: bool, cache_ttl_seconds: int | None) -> Dict[str, Any]:
        ttl = self.DEFAULT_CACHE_TTL_SECONDS if cache_ttl_seconds is None else max(0, int(cache_ttl_seconds))
        cache_key = urlencode(sorted((str(k), str(v)) for k, v in params.items()), doseq=False)
        now = time.time()

        with self._lock:
            if use_cache and ttl > 0:
                cached = self._cache.get(cache_key)
                if cached and (now - cached.created_at) <= ttl:
                    out = copy.deepcopy(cached.payload)
                    out.setdefault("meta", {})
                    out["meta"]["cached"] = True
                    return out
            self._enforce_rate_limit_locked(now)

        url = f"{self.BASE_URL}?{urlencode(params)}"
        xml_payload = self._http_get(url)
        parsed = self._parse_xml(xml_payload)
        parsed["meta"] = {
            "source": "NLM Digital Collections Web Service",
            "base_url": self.BASE_URL,
            "request_url": url,
            "cached": False,
            "fetched_at_epoch": now,
            "request_rate_limit_per_minute": self.MAX_REQUESTS_PER_MINUTE,
        }

        with self._lock:
            if use_cache and ttl > 0:
                self._cache[cache_key] = _CacheEntry(created_at=now, payload=copy.deepcopy(parsed))

        return parsed

    def _enforce_rate_limit_locked(self, now: float) -> None:
        while self._request_times and (now - self._request_times[0]) >= 60.0:
            self._request_times.popleft()
        if len(self._request_times) >= self.MAX_REQUESTS_PER_MINUTE:
            raise NLMDigitalCollectionsRateLimitError(
                f"NLM client request rate would exceed {self.MAX_REQUESTS_PER_MINUTE} requests/minute."
            )
        self._request_times.append(now)

    def _http_get(self, url: str) -> bytes:
        req = Request(url, headers={"User-Agent": "qso-fabric-nlm-plugin/1.0"})
        try:
            with urlopen(req, timeout=20) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - depends on network conditions
            raise NLMDigitalCollectionsClientError(f"unable to fetch NLM response: {exc}") from exc

    def _parse_xml(self, xml_payload: bytes) -> Dict[str, Any]:
        try:
            root = ET.fromstring(xml_payload)
        except ET.ParseError as exc:
            raise NLMDigitalCollectionsClientError(f"invalid XML response: {exc}") from exc

        if root.tag != "nlmSearchResult":
            error_text = "".join(root.itertext()).strip()
            if error_text:
                raise NLMDigitalCollectionsClientError(error_text)
            raise NLMDigitalCollectionsClientError(f"unexpected response root element: {root.tag}")

        list_elem = root.find("list")
        list_attrs = list_elem.attrib if list_elem is not None else {}
        list_meta = {
            "num": self._safe_int(list_attrs.get("num")),
            "start": self._safe_int(list_attrs.get("start")),
            "per": self._safe_int(list_attrs.get("per")),
        }

        documents: list[Dict[str, Any]] = []
        if list_elem is not None:
            for doc in list_elem.findall("document"):
                content: Dict[str, list[str]] = {}
                for node in doc.findall("content"):
                    name = str(node.attrib.get("name", "")).strip()
                    if not name:
                        continue
                    value = "".join(node.itertext()).strip()
                    content.setdefault(name, []).append(value)
                documents.append(
                    {
                        "url": str(doc.attrib.get("url", "")),
                        "rank": self._safe_int(doc.attrib.get("rank")),
                        "content": content,
                    }
                )

        return {
            "term": self._find_text(root, "term"),
            "file": self._find_text(root, "file"),
            "server": self._find_text(root, "server"),
            "count": self._safe_int(self._find_text(root, "count"), default=0),
            "retstart": self._safe_int(self._find_text(root, "retstart"), default=0),
            "retmax": self._safe_int(self._find_text(root, "retmax"), default=0),
            "list": list_meta,
            "documents": documents,
        }

    def _find_text(self, root: ET.Element, tag: str) -> str:
        elem = root.find(tag)
        if elem is None:
            return ""
        return (elem.text or "").strip()

    def _safe_int(self, value: str | None, default: int = 0) -> int:
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return default
