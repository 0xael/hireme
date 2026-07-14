"""Stage 2b: generate a Markdown cover letter from the profile + JD."""
from __future__ import annotations

import json
from typing import Any

from .client import HiremeClient, Usage
from .prompts import COVER_LETTER_SYSTEM


def write_cover_letter(
    client: HiremeClient,
    profile: dict[str, Any],
    job_description: str,
) -> tuple[str, Usage]:
    prompt = (
        "Candidate profile (JSON):\n"
        f"{json.dumps(profile, indent=2)}\n\n"
        "Target job description:\n"
        "<job_description>\n"
        f"{job_description}\n"
        "</job_description>\n\n"
        "Write the cover letter now."
    )

    response = client.call(
        system=COVER_LETTER_SYSTEM,
        prompt=prompt,
        allowed_tools=[],
        timeout_seconds=300,
    )

    if not response.text.strip():
        raise RuntimeError("Claude returned no text for the cover letter.")
    return response.text.strip() + "\n", response.usage
