from __future__ import annotations

from services.quantum.backends.qiskit_backend import QiskitBackend


class PhotonicBackend(QiskitBackend):
    name = "photonic"
