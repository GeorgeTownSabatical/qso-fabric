from __future__ import annotations

import argparse
import html.parser
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from solis.shared.hashing import sha256_hex_obj

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".json", ".html", ".htm"}
STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "because",
    "before",
    "between",
    "for",
    "from",
    "have",
    "into",
    "more",
    "that",
    "the",
    "their",
    "then",
    "there",
    "these",
    "this",
    "through",
    "with",
    "would",
}


class _HTMLTextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = data.strip()
        if cleaned:
            self.parts.append(cleaned)


@dataclass(frozen=True, slots=True)
class WikiPageRecord:
    source_path: str
    wiki_path: str
    title: str
    slug: str
    source_hash: str
    word_count: int
    keywords: list[str]
    linked_pages: list[str]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def _read_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            return json.dumps(json.loads(raw), indent=2, sort_keys=True)
        except json.JSONDecodeError:
            return raw
    if path.suffix.lower() in {".html", ".htm"}:
        parser = _HTMLTextExtractor()
        parser.feed(raw)
        return "\n".join(parser.parts)
    return raw


def _title_for(path: Path, text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.stem
        if stripped:
            return stripped[:80]
    return path.stem.replace("_", " ").replace("-", " ").title()


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text.lower())


def _keywords(text: str, limit: int = 12) -> list[str]:
    counts = Counter(word for word in _words(text) if word not in STOPWORDS)
    return [word for word, _count in counts.most_common(limit)]


def _summary(text: str, word_limit: int = 90) -> str:
    words = re.findall(r"\S+", " ".join(text.split()))
    if len(words) <= word_limit:
        return " ".join(words)
    return " ".join(words[:word_limit]) + "..."


def _iter_sources(raw_dir: Path) -> Iterable[Path]:
    for path in sorted(raw_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            yield path


def ingest_wiki(raw_dir: Path, wiki_dir: Path) -> dict[str, object]:
    raw_dir = raw_dir.resolve()
    wiki_dir.mkdir(parents=True, exist_ok=True)
    source_payloads: list[tuple[Path, str, str, list[str]]] = []
    for source in _iter_sources(raw_dir):
        text = _read_text(source)
        title = _title_for(source, text)
        source_payloads.append((source, text, title, _keywords(text)))

    keyword_by_slug: dict[str, set[str]] = {}
    slug_by_source: dict[Path, str] = {}
    for source, _text, title, keywords in source_payloads:
        slug = _slugify(title)
        original = slug
        suffix = 2
        while slug in keyword_by_slug:
            slug = f"{original}-{suffix}"
            suffix += 1
        slug_by_source[source] = slug
        keyword_by_slug[slug] = set(keywords)

    records: list[WikiPageRecord] = []
    for source, text, title, keywords in source_payloads:
        slug = slug_by_source[source]
        overlaps: list[tuple[str, int]] = []
        current_keywords = set(keywords)
        for other_slug, other_keywords in keyword_by_slug.items():
            if other_slug == slug:
                continue
            score = len(current_keywords & other_keywords)
            if score:
                overlaps.append((other_slug, score))
        linked_pages = [other for other, _score in sorted(overlaps, key=lambda item: (-item[1], item[0]))[:6]]
        wiki_path = wiki_dir / f"{slug}.md"
        source_hash = sha256_hex_obj({"path": str(source.relative_to(raw_dir)), "text": text})
        body = [
            f"# {title}",
            "",
            "## Source",
            "",
            f"- Path: `{source.relative_to(raw_dir)}`",
            f"- SHA-256: `{source_hash}`",
            f"- Word count: `{len(_words(text))}`",
            "",
            "## Summary",
            "",
            _summary(text),
            "",
            "## Keywords",
            "",
            ", ".join(f"`{keyword}`" for keyword in keywords) if keywords else "_No keywords extracted._",
            "",
            "## Related Pages",
            "",
        ]
        if linked_pages:
            body.extend(f"- [[{page}]]" for page in linked_pages)
        else:
            body.append("_No related pages yet._")
        body.extend(["", "## Raw Excerpt", "", "```text", _summary(text, word_limit=160), "```", ""])
        wiki_path.write_text("\n".join(body), encoding="utf-8")
        records.append(
            WikiPageRecord(
                source_path=str(source.relative_to(raw_dir)),
                wiki_path=str(wiki_path.relative_to(wiki_dir)),
                title=title,
                slug=slug,
                source_hash=source_hash,
                word_count=len(_words(text)),
                keywords=keywords,
                linked_pages=linked_pages,
            )
        )

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "raw_dir": str(raw_dir),
        "wiki_dir": str(wiki_dir.resolve()),
        "page_count": len(records),
        "pages": [asdict(record) for record in records],
        "manifest_hash": sha256_hex_obj([asdict(record) for record in records]),
    }
    (wiki_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    index_lines = ["# Wiki Index", "", f"Generated: `{manifest['generated_at']}`", "", "## Pages", ""]
    index_lines.extend(f"- [[{record.slug}]] - {record.title}" for record in records)
    if not records:
        index_lines.append("_No supported source files found._")
    (wiki_dir / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest raw source files into a deterministic QSO living wiki")
    parser.add_argument("--raw-dir", default="raw")
    parser.add_argument("--wiki-dir", default="wiki")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    manifest = ingest_wiki(Path(args.raw_dir), Path(args.wiki_dir))
    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return
    print(f"ingested {manifest['page_count']} source file(s)")
    print(f"wiki_dir={manifest['wiki_dir']}")
    print(f"manifest_hash={manifest['manifest_hash']}")


if __name__ == "__main__":
    main()
