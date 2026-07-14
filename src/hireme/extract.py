"""Stage 1: extract a tailored candidate profile from the old CV PDF + job description."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .client import ClaudeCLIError, HiremeClient, Usage
from .prompts import EXTRACT_SYSTEM, PROFILE_JSON_SCHEMA


def extract_profile(
    client: HiremeClient,
    cv_pdf_path: Path,
    job_description: str,
) -> tuple[dict[str, Any], Usage]:
    cv_pdf_path = cv_pdf_path.resolve()
    if not cv_pdf_path.exists():
        raise FileNotFoundError(cv_pdf_path)

    prompt = (
        f"The candidate's existing CV is at this path:\n"
        f"  {cv_pdf_path}\n\n"
        f"Read that PDF now using your Read tool, then produce the tailored profile.\n\n"
        f"Target job description:\n"
        f"<job_description>\n"
        f"{job_description}\n"
        f"</job_description>\n\n"
        f"Return the structured profile matching the JSON schema."
    )

    response = client.call(
        system=EXTRACT_SYSTEM,
        prompt=prompt,
        json_schema=PROFILE_JSON_SCHEMA,
        add_dirs=[cv_pdf_path.parent],
        allowed_tools=["Read"],
        timeout_seconds=600,
    )

    if response.structured is None:
        raise ClaudeCLIError(
            "Claude did not return structured output. "
            f"Text was: {response.text[:500]!r}"
        )

    return response.structured, response.usage
