# hireme

CLI that generates a tailored LaTeX CV and a Markdown cover letter from an old CV (PDF) and a job description, using a LaTeX template you provide.

Under the hood, `hireme` shells out to the local [`claude`](https://docs.claude.com/en/docs/claude-code/overview) CLI in headless mode, so it uses whatever authentication your `claude` install already has — no separate `ANTHROPIC_API_KEY` required.

## Setup

```bash
pip install -e .
```

Make sure the `claude` CLI is installed and you're logged in (`claude auth status`). Drop your LaTeX template at `templates/cv.tex`. The generated CV will reuse its preamble, macros, and section structure exactly — only the content changes.

Optionally, copy `.env.example` to `.env` to pin a model or override the `claude` binary path.

## Usage

```bash
hireme generate \
    --cv path/to/old_cv.pdf \
    --job path/to/job_description.txt \
    --template templates/cv.tex \
    --out out/
```

Outputs land in `out/`:
- `cv.tex` — compile with your own `pdflatex` / `xelatex` toolchain.
- `cover_letter.md` — Markdown cover letter.
- `profile.json` — the structured profile extracted from the CV (useful for debugging).

## How it works

Three-stage pipeline:

1. **Extract** — `claude` reads the CV PDF and the job description, and returns a tailored candidate profile as JSON (validated against a strict schema via `--json-schema`).
2. **Fill CV** — `claude` fills your LaTeX template with the profile, preserving preamble and macros exactly. A post-generation check warns if any new `\usepackage` or `\newcommand` lines were added.
3. **Cover letter** — `claude` writes a concise Markdown cover letter grounded in the extracted profile.
