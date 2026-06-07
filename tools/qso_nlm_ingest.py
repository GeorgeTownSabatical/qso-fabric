from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.mcp_tools.qso_tools import QSOMCPTools
from core.naming.snapshot_terms import resolve_snapshot_artifact_path
from services.plugins.nlm_client import (
    NLMDigitalCollectionsClient,
    NLMDigitalCollectionsClientError,
    NLMDigitalCollectionsRateLimitError,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or refresh a QSO object populated with NLM Digital Collections metadata."
    )
    parser.add_argument(
        "--root-uri",
        default="qso://knowledge.nlm.digital_collections",
        help="QSO URI to create/update with ingested NLM documents.",
    )
    parser.add_argument(
        "--term",
        default="dc:identifier:http",
        help="Initial NLM query term. Default targets identifier field to maximize corpus coverage.",
    )
    parser.add_argument("--retmax", type=int, default=50, help="NLM page size for each request (1..200).")
    parser.add_argument("--max-docs", type=int, default=300, help="Maximum docs to ingest into the QSO payload.")
    parser.add_argument("--max-pages", type=int, default=50, help="Maximum request pages to pull from NLM.")
    parser.add_argument("--tool", default="qso_nlm_ingest", help="NLM tool identifier.")
    parser.add_argument("--email", default="", help="Optional NLM contact email parameter.")
    parser.add_argument("--no-cache", action="store_true", help="Disable local NLM response cache.")
    parser.add_argument("--cache-ttl-seconds", type=int, default=12 * 60 * 60, help="Local cache TTL in seconds.")
    parser.add_argument(
        "--snapshot-out",
        default=str(resolve_snapshot_artifact_path("nlm_knowledge.qff")),
        help="Optional QFF snapshot output path (empty string disables snapshot export).",
    )
    parser.add_argument(
        "--summary-json",
        default="",
        help="Optional path to write ingestion summary JSON (empty disables summary file).",
    )
    parser.add_argument("--progress", action="store_true", help="Print per-page progress.")
    return parser


def _strip_highlight(value: str) -> str:
    # NLM response may include <span class="qt0">...</span> markers.
    out = value.replace("<span class=\"qt0\">", "").replace("</span>", "")
    return out.strip()


def _first(content: dict[str, Any], key: str) -> str:
    values = content.get(key, [])
    if not isinstance(values, list) or not values:
        return ""
    return _strip_highlight(str(values[0]))


def _normalize_document(doc: dict[str, Any]) -> dict[str, Any]:
    content = doc.get("content", {})
    content = content if isinstance(content, dict) else {}
    url = str(doc.get("url", "")).strip()
    title = _first(content, "dc:title")
    snippet = _first(content, "snippet")
    record_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16] if url else ""
    return {
        "record_id": record_id,
        "url": url,
        "rank": int(doc.get("rank", 0) or 0),
        "title": title,
        "snippet": snippet,
        "publication": _first(content, "Publication"),
        "date": _first(content, "dc:date"),
        "language": _first(content, "dc:language"),
        "subjects": [str(x).strip() for x in content.get("dc:subject", []) if str(x).strip()],
        "raw_content": content,
    }


def _fetch_with_retry(func, *, max_retries: int = 5):
    for attempt in range(max_retries + 1):
        try:
            return func()
        except NLMDigitalCollectionsRateLimitError:
            if attempt >= max_retries:
                raise
            time.sleep(1.0 + attempt * 0.5)


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.max_docs < 1:
        parser.error("--max-docs must be >= 1")
    if args.max_pages < 1:
        parser.error("--max-pages must be >= 1")

    client = NLMDigitalCollectionsClient(
        tool=str(args.tool).strip() or "qso_nlm_ingest",
        email=(str(args.email).strip() or None),
    )
    tools = QSOMCPTools()

    query_term = str(args.term).strip()
    if not query_term:
        parser.error("--term must not be empty")

    pages = 0
    total_count = 0
    file_token = ""
    server_token = ""
    retstart = 0
    unique_by_url: dict[str, dict[str, Any]] = {}

    try:
        payload = _fetch_with_retry(
            lambda: client.search(
                term=query_term,
                retmax=args.retmax,
                use_cache=not bool(args.no_cache),
                cache_ttl_seconds=args.cache_ttl_seconds,
            )
        )
    except NLMDigitalCollectionsClientError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except NLMDigitalCollectionsRateLimitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    while True:
        pages += 1
        total_count = int(payload.get("count", total_count) or total_count)
        file_token = str(payload.get("file", file_token)).strip()
        server_token = str(payload.get("server", server_token)).strip()
        docs = payload.get("documents", [])
        docs = docs if isinstance(docs, list) else []

        for raw_doc in docs:
            if not isinstance(raw_doc, dict):
                continue
            normalized = _normalize_document(raw_doc)
            url = normalized.get("url", "")
            if not url:
                continue
            unique_by_url[url] = normalized
            if len(unique_by_url) >= args.max_docs:
                break

        if args.progress:
            print(
                f"page={pages} loaded={len(docs)} unique={len(unique_by_url)} count={total_count} retstart={retstart}",
                file=sys.stderr,
            )

        if len(unique_by_url) >= args.max_docs:
            break
        if pages >= args.max_pages:
            break
        if not file_token or not server_token:
            break

        retstart += len(docs)
        if retstart >= total_count and total_count > 0:
            break

        try:
            payload = _fetch_with_retry(
                lambda: client.continue_search(
                    file=file_token,
                    server=server_token,
                    retstart=retstart,
                    retmax=args.retmax,
                    use_cache=not bool(args.no_cache),
                    cache_ttl_seconds=args.cache_ttl_seconds,
                )
            )
        except NLMDigitalCollectionsClientError as exc:
            print(f"warning: stopping early due to NLM continuation error: {exc}", file=sys.stderr)
            break
        except NLMDigitalCollectionsRateLimitError as exc:
            print(f"warning: stopping early due to rate-limit pressure: {exc}", file=sys.stderr)
            break

    documents = sorted(unique_by_url.values(), key=lambda d: (d.get("rank", 0), d.get("url", "")))[: args.max_docs]
    created_at = _iso_now()
    state = {
        "kind": "knowledge_node",
        "source": "NLM Digital Collections Web Service",
        "base_url": NLMDigitalCollectionsClient.BASE_URL,
        "query": {
            "term": query_term,
            "retmax": int(args.retmax),
            "file": file_token,
            "server": server_token,
        },
        "ingestion": {
            "generated_at": created_at,
            "pages_fetched": pages,
            "max_pages": int(args.max_pages),
            "total_matches_reported": total_count,
            "documents_ingested": len(documents),
            "max_docs": int(args.max_docs),
            "cache_enabled": not bool(args.no_cache),
            "cache_ttl_seconds": int(args.cache_ttl_seconds),
            "rate_limit_per_minute": NLMDigitalCollectionsClient.MAX_REQUESTS_PER_MINUTE,
        },
        "query_contract": {
            "required_initial_parameters": ["db", "term"],
            "required_subsequent_parameters": ["file", "server", "retstart"],
            "optional_parameters": ["retmax", "tool", "email"],
            "response_root": "nlmSearchResult",
            "response_format": "xml",
        },
        "documents": documents,
    }

    try:
        tools.qso_create(uri=args.root_uri, schema={"type": "nlm_knowledge_qso"})
    except Exception:
        pass
    tools.qso_patch(
        uri=args.root_uri,
        delta=state,
        actor="qso-nlm-ingest",
        policy_version="v1",
        node_id="cli",
    )

    snapshot_path = str(args.snapshot_out).strip()
    if snapshot_path:
        blob = tools.qso_export_snapshot(args.root_uri)
        output = Path(snapshot_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(blob)

    summary = {
        "status": "ok",
        "root_uri": args.root_uri,
        "documents_ingested": len(documents),
        "total_matches_reported": total_count,
        "pages_fetched": pages,
        "query_term": query_term,
        "snapshot_out": snapshot_path,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=True))

    summary_json = str(args.summary_json).strip()
    if summary_json:
        out = Path(summary_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
