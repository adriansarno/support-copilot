"""API-specific settings, extending shared config."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared.config import Settings


@lru_cache
def get_api_settings() -> Settings:
    return Settings()
