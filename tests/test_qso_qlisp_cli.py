from __future__ import annotations

import json
from pathlib import Path

from tools.qso_qlisp import main


def test_qso_qlisp_compile_cli(capsys, tmp_path: Path) -> None:
    source = tmp_path / "program.qlisp"
    source.write_text("(observe obs :source qso://memory/demo)\n(reason :goal obs)\n", encoding="utf-8")
    main(["compile", str(source)])
    payload = json.loads(capsys.readouterr().out)
    assert payload["backend_targets"] == ["fabric_gluing"]
    assert len(payload["ir_hash"]) == 64
