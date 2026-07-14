"""Config: environment loading."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL: str | None = None  # None -> let `claude` pick its default


@dataclass(frozen=True)
class Config:
    model: str | None
    claude_bin: str

    @classmethod
    def from_env(cls) -> "Config":
        model = os.environ.get("HIREME_MODEL", "").strip() or DEFAULT_MODEL
        claude_bin = os.environ.get("HIREME_CLAUDE_BIN", "").strip() or "claude"
        return cls(model=model, claude_bin=claude_bin)
