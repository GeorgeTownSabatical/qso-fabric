from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

from services.plugins.nlm_client import (
    NLMDigitalCollectionsClient,
    NLMDigitalCollectionsClientError,
    NLMDigitalCollectionsRateLimitError,
)


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(value: str) -> str:
    return _TAG_RE.sub("", value).strip()


def _first_content(doc: dict[str, Any], key: str) -> str:
    content = doc.get("content", {})
    if not isinstance(content, dict):
        return ""
    values = content.get(key, [])
    if not isinstance(values, list) or not values:
        return ""
    return str(values[0]).strip()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query NLM Digital Collections Web Service.")
    parser.add_argument("--term", help="Initial search term for db=digitalCollections.")
    parser.add_argument("--file", help="Continuation search file token from prior response.")
    parser.add_argument("--server", help="Continuation search server token from prior response.")
    parser.add_argument("--retstart", type=int, help="Continuation offset (required with --file/--server).")
    parser.add_argument("--retmax", type=int, default=10, help="Number of documents to return (default: 10).")
    parser.add_argument("--tool", default="qso_nlm_search", help="NLM tool identifier string.")
    parser.add_argument("--email", default="", help="Optional contact email passed to NLM.")
    parser.add_argument(
        "--cache-ttl-seconds",
        type=int,
        default=12 * 60 * 60,
        help="Local cache TTL in seconds (default: 43200).",
    )
    parser.add_argument("--no-cache", action="store_true", help="Disable local result caching.")
    parser.add_argument("--json", action="store_true", help="Emit full JSON payload.")
    parser.add_argument("--show-snippets", action="store_true", help="Include snippet lines in text output.")
    return parser


def _validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    has_term = bool(str(args.term or "").strip())
    has_continuation = any(
        bool(str(value or "").strip()) for value in (args.file, args.server)
    ) or args.retstart is not None

    if has_term and has_continuation:
        parser.error("Use either --term (initial search) or continuation args (--file/--server/--retstart), not both.")
    if not has_term and not has_continuation:
        parser.error("Provide --term for initial search, or --file --server --retstart for continuation.")

    if has_continuation:
        if not str(args.file or "").strip():
            parser.error("--file is required for continuation search.")
        if not str(args.server or "").strip():
            parser.error("--server is required for continuation search.")
        if args.retstart is None:
            parser.error("--retstart is required for continuation search.")
        if args.retstart < 0:
            parser.error("--retstart must be a non-negative integer.")


def _print_summary(payload: dict[str, Any], *, show_snippets: bool) -> None:
    term = str(payload.get("term", "")).strip()
    count = int(payload.get("count", 0) or 0)
    retstart = int(payload.get("retstart", 0) or 0)
    retmax = int(payload.get("retmax", 0) or 0)
    file_token = str(payload.get("file", "")).strip()
    server_token = str(payload.get("server", "")).strip()
    meta = payload.get("meta", {}) if isinstance(payload.get("meta"), dict) else {}
    cached = bool(meta.get("cached", False))
    request_url = str(meta.get("request_url", "")).strip()

    print(f"term: {term}")
    print(f"count: {count}  retstart: {retstart}  retmax: {retmax}  cached: {cached}")
    if file_token and server_token:
        print(f"file: {file_token}")
        print(f"server: {server_token}")
    if request_url:
        print(f"url: {request_url}")

    docs = payload.get("documents", [])
    if not isinstance(docs, list) or not docs:
        print("documents: 0")
        return

    print(f"documents: {len(docs)}")
    for idx, doc in enumerate(docs, start=1):
        if not isinstance(doc, dict):
            continue
        title = _strip_tags(_first_content(doc, "dc:title"))
        snippet = _strip_tags(_first_content(doc, "snippet"))
        rank = doc.get("rank")
        url = str(doc.get("url", "")).strip()

        print(f"{idx}. rank={rank} title={title or '(untitled)'}")
        if url:
            print(f"   url={url}")
        if show_snippets and snippet:
            print(f"   snippet={snippet}")


def run(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _validate_args(args, parser)

    client = NLMDigitalCollectionsClient(
        tool=str(args.tool).strip() or "qso_nlm_search",
        email=(str(args.email).strip() or None),
    )

    try:
        if str(args.term or "").strip():
            payload = client.search(
                term=str(args.term).strip(),
                retmax=args.retmax,
                use_cache=not bool(args.no_cache),
                cache_ttl_seconds=args.cache_ttl_seconds,
            )
        else:
            payload = client.continue_search(
                file=str(args.file),
                server=str(args.server),
                retstart=int(args.retstart),
                retmax=args.retmax,
                use_cache=not bool(args.no_cache),
                cache_ttl_seconds=args.cache_ttl_seconds,
            )
    except NLMDigitalCollectionsRateLimitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except NLMDigitalCollectionsClientError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=True))
    else:
        _print_summary(payload, show_snippets=bool(args.show_snippets))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
