"""Art backend dispatch: profile-aware art module resolution.

`stickman(kind)` returns the stickman art module when APP_PROFILE=stickman,
else None (default Fernwood art). Base art functions self-dispatch at call
time through this module; assets.py resolves tuples (SPECIES/POSES/FACES/
LOCATIONS/PROPS) at build time via `art_module(kind)`.
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any

_STICKMAN_KINDS = ("characters", "locations", "props")
_MOD_CACHE: dict[tuple[str, str], ModuleType] = {}


def stickman(kind: str) -> ModuleType | None:
    """Stickman art module for kind, or None on the default profile."""
    if kind not in _STICKMAN_KINDS:
        raise KeyError(f"Unknown art kind: {kind}")
    prof = _active_profile()
    if prof != "stickman":
        return None
    key = (prof, kind)
    mod = _MOD_CACHE.get(key)
    if mod is None:
        mod = importlib.import_module(f"{__package__}.stickman_{kind}")
        _MOD_CACHE[key] = mod
    return mod


def art_module(kind: str) -> ModuleType:
    """Active art module for kind (stickman overrides, else Fernwood base)."""
    return stickman(kind) or importlib.import_module(f"{__package__}.{kind}")


def _active_profile() -> str:
    try:
        from ...config import profile
        return profile()
    except Exception:
        return ""


def spec(kind: str, name: str) -> Any:
    """Module-level constant from the active art module (e.g. LOCATIONS)."""
    return getattr(art_module(kind), name)
