# QSO Fabric Distributed Federation Design

Federation model:
- event replication + policy compatibility + deterministic replay
- no shared mutable central database

Node roles:
- standard, anchor, observer, optional GDML coordinator

Safety rules:
- runtime version compatibility check
- policy handshake before applying unknown versions
- checkpoint hash validation
- deterministic reconciliation after partition recovery
