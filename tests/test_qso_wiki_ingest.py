from __future__ import annotations

import json
from pathlib import Path

from tools.qso_wiki_ingest import ingest_wiki


def test_wiki_ingest_creates_pages_manifest_and_links(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    wiki = tmp_path / "wiki"
    raw.mkdir()
    (raw / "alpha.md").write_text("# Alpha Memory\nQuantum LISP reasoning links memory and repair.", encoding="utf-8")
    (raw / "beta.txt").write_text("Beta note about memory repair and replayable state.", encoding="utf-8")

    manifest = ingest_wiki(raw, wiki)

    assert manifest["page_count"] == 2
    assert (wiki / "index.md").exists()
    assert (wiki / "manifest.json").exists()
    assert (wiki / "alpha-memory.md").exists()
    page_text = (wiki / "alpha-memory.md").read_text(encoding="utf-8")
    assert "## Related Pages" in page_text
    assert "[[beta-note-about-memory-repair-and-replayable-state]]" in page_text

    on_disk = json.loads((wiki / "manifest.json").read_text(encoding="utf-8"))
    assert on_disk["manifest_hash"] == manifest["manifest_hash"]
