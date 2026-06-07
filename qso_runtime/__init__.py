from __future__ import annotations

from services.runtime import QSOFabricRuntime


class LegacyRuntimeFacade:
    """Compatibility facade for older qso_runtime imports.

    The canonical runtime implementation is services.runtime.QSOFabricRuntime.
    """

    def __init__(self) -> None:
        self.runtime = QSOFabricRuntime()


__all__ = ["LegacyRuntimeFacade", "QSOFabricRuntime"]
