"""Stage 2a: fill the LaTeX template with the tailored profile."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .client import HiremeClient, Usage
from .prompts import FILL_CV_SYSTEM_TEMPLATE

_USEPACKAGE_RE = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}")
_NEWCOMMAND_RE = re.compile(r"\\(?:new|renew|providecommand)\{?\\([A-Za-z@]+)")


def fill_cv(
    client: HiremeClient,
    template_path: Path,
    profile: dict[str, Any],
) -> tuple[str, Usage, list[str]]:
    """Returns (tex_source, usage, warnings)."""
    template = template_path.read_text(encoding="utf-8")
    system = FILL_CV_SYSTEM_TEMPLATE.format(template=template)

    prompt = (
        "Candidate profile (JSON):\n"
        f"{json.dumps(profile, indent=2)}\n\n"
        "Produce the complete .tex source now."
    )

    response = client.call(
        system=system,
        prompt=prompt,
        allowed_tools=[],
        timeout_seconds=600,
    )

    tex_source = _strip_fences(response.text.strip())
    if not tex_source:
        raise RuntimeError("Claude returned no text for the CV.")

    warnings = _validate_structure(template, tex_source)
    return tex_source, response.usage, warnings


def _strip_fences(text: str) -> str:
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)
    return text


def _validate_structure(template: str, generated: str) -> list[str]:
    warnings: list[str] = []

    tpl_pkgs = set(_USEPACKAGE_RE.findall(template))
    gen_pkgs = set(_USEPACKAGE_RE.findall(generated))
    added = gen_pkgs - tpl_pkgs
    removed = tpl_pkgs - gen_pkgs
    if added:
        warnings.append(f"Generated CV added new packages not in template: {sorted(added)}")
    if removed:
        warnings.append(f"Generated CV dropped packages present in template: {sorted(removed)}")

    tpl_cmds = set(_NEWCOMMAND_RE.findall(template))
    gen_cmds = set(_NEWCOMMAND_RE.findall(generated))
    added_cmds = gen_cmds - tpl_cmds
    if added_cmds:
        warnings.append(
            f"Generated CV defined new commands not in template: {sorted(added_cmds)}"
        )

    if "\\begin{document}" not in generated or "\\end{document}" not in generated:
        warnings.append("Generated CV is missing \\begin{document} or \\end{document}.")

    return warnings
