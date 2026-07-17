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
from .job_meta import extract_job_meta, slugify


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

    click.echo("[1/4] Identifying target company and position...")
    meta, meta_usage = extract_job_meta(client, job_description)
    company = meta["company"]
    position = meta["position"]
    company_slug = slugify(company, lowercase=True)
    prefix = f"{slugify(company)}_{slugify(position)}"
    job_dir = out_dir / company_slug
    job_dir.mkdir(parents=True, exist_ok=True)
    click.echo(
        f"      company={company!r} position={position!r} -> {job_dir}/  [{meta_usage.summary()}]"
    )

    click.echo(f"[2/4] Extracting tailored profile from {cv_path.name}...")
    profile, extract_usage = extract_profile(client, cv_path, job_description)
    profile_path = job_dir / "profile.json"
    profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    click.echo(f"      wrote {profile_path}  [{extract_usage.summary()}]")

    click.echo(f"[3/4] Filling LaTeX template {template_path}...")
    tex_source, fill_usage, warnings = fill_cv(client, template_path, profile)
    cv_out = job_dir / f"{prefix}_cv.tex"
    cv_out.write_text(tex_source, encoding="utf-8")
    click.echo(f"      wrote {cv_out}  [{fill_usage.summary()}]")
    for w in warnings:
        click.echo(f"      WARNING: {w}", err=True)

    click.echo("[4/4] Writing cover letter...")
    letter, letter_usage = write_cover_letter(client, profile, job_description)
    letter_out = job_dir / f"{prefix}_cover_letter.md"
    letter_out.write_text(letter, encoding="utf-8")
    click.echo(f"      wrote {letter_out}  [{letter_usage.summary()}]")

    click.echo("Done.")


if __name__ == "__main__":
    main()
