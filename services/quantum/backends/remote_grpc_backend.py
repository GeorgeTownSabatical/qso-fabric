from __future__ import annotations

from services.quantum.backends.qiskit_backend import QiskitBackend


class RemoteGrpcBackend(QiskitBackend):
    name = "remote_grpc"
