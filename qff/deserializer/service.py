from __future__ import annotations

import gzip
import io
import json
import tarfile
from typing import Any, Dict


class QFFDeserializer:
    def deserialize(self, blob: bytes) -> Dict[str, Any]:
        raw = gzip.decompress(blob)
        by_name: Dict[str, bytes] = {}
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r") as tar:
            for member in tar.getmembers():
                if member.isfile():
                    f = tar.extractfile(member)
                    if f:
                        by_name[member.name] = f.read()

        required = ("header.json", "state_index.bin", "entanglement.map", "crypto.sig")
        missing = [name for name in required if name not in by_name]
        if missing:
            raise ValueError(f"invalid QFF snapshot, missing required entries: {', '.join(sorted(missing))}")

        return {
            "header": json.loads(by_name["header.json"].decode("utf-8")),
            "state": json.loads(by_name["state_index.bin"].decode("utf-8")),
            "entanglement": json.loads(by_name["entanglement.map"].decode("utf-8")),
            "signature": by_name["crypto.sig"].decode("utf-8"),
        }
