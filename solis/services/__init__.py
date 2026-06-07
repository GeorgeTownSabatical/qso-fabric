from typing import Any

__all__ = [
    "QSOBridge",
    "SolisConstellationService",
    "SolisMetaSignalService",
    "SolisStarService",
    "SolisQSOBridge",
]


def __getattr__(name: str) -> Any:
    if name == "QSOBridge":
        from solis.services.qso_bridge import QSOBridge as _QSOBridge

        return _QSOBridge
    if name == "SolisConstellationService":
        from solis.services.solis_constellation_service import SolisConstellationService as _SolisConstellationService

        return _SolisConstellationService
    if name == "SolisMetaSignalService":
        from solis.services.solis_meta_signal_service import SolisMetaSignalService as _SolisMetaSignalService

        return _SolisMetaSignalService
    if name == "SolisStarService":
        from solis.services.solis_star_service import SolisStarService as _SolisStarService

        return _SolisStarService
    if name == "SolisQSOBridge":
        from solis.services.solis_star_service import SolisQSOBridge as _SolisQSOBridge

        return _SolisQSOBridge
    raise AttributeError(name)
