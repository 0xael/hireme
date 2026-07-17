"""Stage 0: extract the target company + position from the job description."""
from __future__ import annotations

import re
from typing import Any

from .client import ClaudeCLIError, HiremeClient, Usage
from .prompts import JOB_META_SCHEMA, JOB_META_SYSTEM


def extract_job_meta(
    client: HiremeClient,
    job_description: str,
) -> tuple[dict[str, str], Usage]:
    prompt = (
        "Target job description:\n"
        "<job_description>\n"
        f"{job_description}\n"
        "</job_description>\n\n"
        "Return the company name and the position title."
    )

    response = client.call(
        system=JOB_META_SYSTEM,
        prompt=prompt,
        json_schema=JOB_META_SCHEMA,
        allowed_tools=[],
        timeout_seconds=120,
    )

    if response.structured is None:
        raise ClaudeCLIError(
            "Claude did not return structured job metadata. "
            f"Text was: {response.text[:500]!r}"
        )

    company = (response.structured.get("company") or "").strip()
    position = (response.structured.get("position") or "").strip()
    if not company or not position:
        raise ClaudeCLIError(
            f"Job metadata missing fields: company={company!r} position={position!r}"
        )
    return {"company": company, "position": position}, response.usage


_SLUG_RE = re.compile(r"[^A-Za-z0-9]+")


def slugify(value: str, *, lowercase: bool = False) -> str:
    """Collapse runs of non-alphanumerics into single underscores.

    Used for both the folder name (lowercase) and the filename prefix (title-case preserved).
    """
    slug = _SLUG_RE.sub("_", value).strip("_")
    return slug.lower() if lowercase else slug
