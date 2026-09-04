from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class DataPaths:
    root: Path
    catalog: Path
    objects: Path

    @classmethod
    def resolve(
        cls,
        override: Path | str | None = None,
        *,
        environment: Mapping[str, str] | None = None,
        platform: str | None = None,
        home: Path | None = None,
    ) -> "DataPaths":
        environment = os.environ if environment is None else environment
        platform = sys.platform if platform is None else platform
        home = Path.home() if home is None else home

        configured = override or environment.get("DEVHARNESS_DATA_DIR")
        if configured:
            root = Path(configured).expanduser().resolve()
        elif platform == "darwin":
            root = home / "Library" / "Application Support" / "DevHarness"
        elif platform == "win32":
            local_app_data = environment.get("LOCALAPPDATA")
            root = (
                Path(local_app_data)
                if local_app_data
                else home / "AppData" / "Local"
            ) / "DevHarness"
        else:
            xdg_data_home = environment.get("XDG_DATA_HOME")
            root = (
                Path(xdg_data_home) if xdg_data_home else home / ".local" / "share"
            ) / "DevHarness"

        return cls(root=root, catalog=root / "catalog.sqlite3", objects=root / "objects")
