"""CLI entry point."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from .client import HiremeClient
from .config import Config
from .cover_letter import write_cover_letter
from .extract import extract_profile
from .fill_cv import fill_cv


@click.group()
def main() -> None:
    """hireme — generate a tailored LaTeX CV and cover letter."""


@main.command()
@click.option(
    "--cv",
    "cv_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the candidate's existing CV as a PDF.",
)
@click.option(
    "--job",
    "job_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to a text file containing the target job description.",
)
@click.option(
    "--template",
    "template_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("templates/cv.tex"),
    show_default=True,
    help="Path to the LaTeX CV template.",
)
@click.option(
    "--out",
    "out_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("out"),
    show_default=True,
    help="Directory to write generated artifacts into.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Stream the underlying `claude` CLI stderr so you can see what each stage is doing.",
)
def generate(
    cv_path: Path,
    job_path: Path,
    template_path: Path,
    out_dir: Path,
    verbose: bool,
) -> None:
    """Generate a tailored CV (.tex) and cover letter (.md)."""
    config = Config.from_env()
    client = HiremeClient(
        model=config.model, claude_bin=config.claude_bin, verbose=verbose
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    job_description = job_path.read_text(encoding="utf-8").strip()
    if not job_description:
        click.echo("Job description file is empty.", err=True)
        sys.exit(1)

    click.echo(f"[1/3] Extracting tailored profile from {cv_path.name}...")
    profile, extract_usage = extract_profile(client, cv_path, job_description)
    profile_path = out_dir / "profile.json"
    profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    click.echo(f"      wrote {profile_path}  [{extract_usage.summary()}]")

    click.echo(f"[2/3] Filling LaTeX template {template_path}...")
    tex_source, fill_usage, warnings = fill_cv(client, template_path, profile)
    cv_out = out_dir / "cv.tex"
    cv_out.write_text(tex_source, encoding="utf-8")
    click.echo(f"      wrote {cv_out}  [{fill_usage.summary()}]")
    for w in warnings:
        click.echo(f"      WARNING: {w}", err=True)

    click.echo("[3/3] Writing cover letter...")
    letter, letter_usage = write_cover_letter(client, profile, job_description)
    letter_out = out_dir / "cover_letter.md"
    letter_out.write_text(letter, encoding="utf-8")
    click.echo(f"      wrote {letter_out}  [{letter_usage.summary()}]")

    click.echo("Done.")


if __name__ == "__main__":
    main()
