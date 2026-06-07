from __future__ import annotations

from qff.deserializer.service import QFFDeserializer
from qff.serializer.service import QFFSerializer


class Serializer:
    def __init__(self) -> None:
        self._ser = QFFSerializer()
        self._de = QFFDeserializer()

    def serialize(self, state: dict) -> bytes:
        return self._ser.serialize(state)

    def deserialize(self, data: bytes) -> dict:
        return self._de.deserialize(data)
