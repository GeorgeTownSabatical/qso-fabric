from __future__ import annotations

import gzip
import io
import json
import tarfile
from typing import Any, Dict


class QFFSerializer:
    def serialize(self, payload: Dict[str, Any]) -> bytes:
        state_bytes = json.dumps(payload["state"], sort_keys=True).encode("utf-8")
        ent_map = json.dumps(payload["entanglement"], sort_keys=True).encode("utf-8")
        header = json.dumps(payload["header"], sort_keys=True).encode("utf-8")

        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w") as tar:
            self._add_file(tar, "header.json", header)
            self._add_file(tar, "state_index.bin", state_bytes)
            self._add_file(tar, "entanglement.map", ent_map)
            self._add_file(tar, "crypto.sig", payload["signature"].encode("utf-8"))
            self._add_file(tar, "footer.bin", b"QFFv1")
            self._add_file(tar, "tensor_blocks/.keep", b"")
            self._add_file(tar, "wave_blocks/.keep", b"")

        return gzip.compress(raw.getvalue())

    @staticmethod
    def _add_file(tar: tarfile.TarFile, name: str, data: bytes) -> None:
        info = tarfile.TarInfo(name=name)
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
