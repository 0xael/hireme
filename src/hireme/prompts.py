"""All prompt strings live here."""
from __future__ import annotations

JOB_META_SYSTEM = """\
You are given a job posting. Extract exactly two fields:
- company: the hiring company's name, as written in the posting (no legal suffixes like GmbH/Inc./Ltd. unless the posting uses no other form).
- position: the job title being advertised, as written in the posting.

Rules:
- Use ONLY what is present in the posting. Do not guess.
- Keep the position concise (drop trailing "(m/f/d)", "(all genders)", location suffixes, seniority markers only if they are decorative — keep them if they are part of the title).
- Return the structured JSON only, no prose."""


JOB_META_SCHEMA = {
    "type": "object",
    "properties": {
        "company": {"type": "string"},
        "position": {"type": "string"},
    },
    "required": ["company", "position"],
}


EXTRACT_SYSTEM = """\
You are an expert CV analyst. You are given (1) a candidate's existing CV as an attached PDF \
and (2) a target job description. Your task is to produce a structured profile of the \
candidate that is TAILORED to the job description.

Rules:
- Use ONLY facts that are present in the attached CV. Do NOT fabricate experience, skills, \
  dates, employers, or achievements.
- Rewrite bullets and the summary to emphasize the aspects most relevant to the job \
  description, using the job description's vocabulary where it is honestly applicable.
- If the CV lacks a particular section (e.g., no projects, no certifications), return an \
  empty list for that section — do not invent one.
- Preserve dates, employer names, and titles exactly as in the CV.
- Group skills by category when the underlying CV supports doing so; otherwise return a \
  single flat group.

Return the structured profile matching the required JSON schema. Do not respond with prose."""


PROFILE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
            "contact": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "location": {"type": "string"},
                    "links": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "url": {"type": "string"},
                            },
                            "required": ["label", "url"],
                        },
                    },
                },
                "required": ["name"],
            },
            "summary": {
                "type": "string",
                "description": "2-4 sentence professional summary tailored to the job description.",
            },
            "skills": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "items": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["category", "items"],
                },
            },
            "experience": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "company": {"type": "string"},
                        "role": {"type": "string"},
                        "location": {"type": "string"},
                        "start": {"type": "string"},
                        "end": {"type": "string", "description": "'Present' if current."},
                        "bullets": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["company", "role", "start", "end", "bullets"],
                },
            },
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "institution": {"type": "string"},
                        "degree": {"type": "string"},
                        "field": {"type": "string"},
                        "start": {"type": "string"},
                        "end": {"type": "string"},
                        "details": {"type": "string"},
                    },
                    "required": ["institution", "degree"],
                },
            },
            "projects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "tech": {"type": "array", "items": {"type": "string"}},
                        "url": {"type": "string"},
                    },
                    "required": ["name", "description"],
                },
            },
            "certifications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "issuer": {"type": "string"},
                        "year": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
        },
    "required": ["contact", "summary", "skills", "experience", "education"],
}


FILL_CV_SYSTEM_TEMPLATE = """\
You are a LaTeX CV generator. You will be given a candidate profile as JSON, and you must \
produce a complete .tex document by filling in the following template with the candidate's \
information.

CRITICAL RULES — the generated .tex MUST follow the template's structure exactly:
1. Use ONLY the LaTeX commands, environments, and section macros that appear in the \
   template below. Do NOT invent new commands.
2. Keep the preamble (everything before \\begin{{document}}) IDENTICAL to the template — \
   same \\documentclass, same \\usepackage lines, same \\newcommand definitions, same order.
3. Do NOT add new \\usepackage, \\newcommand, or \\renewcommand lines.
4. Use the same section headings and the same content-item macros the template demonstrates \
   (e.g., if it uses \\cventry, use \\cventry; if it uses a custom \\jobEntry, use that).
5. Escape LaTeX special characters in content (&, %, $, #, _, {{, }}, ~, ^, \\) properly.
6. If the profile lacks data for an optional section, omit that section rather than \
   leaving placeholders.

OUTPUT FORMAT: Return ONLY the raw LaTeX source. No markdown fences, no commentary, no \
explanation. The very first characters of your response must be the start of the .tex file \
(typically `\\documentclass`), and the last characters must be `\\end{{document}}`.

<template>
{template}
</template>"""


COVER_LETTER_SYSTEM = """\
You write concise, specific cover letters in Markdown.

Rules:
- 3 to 4 short paragraphs. Aim for 200-320 words total.
- Reference concrete achievements from the candidate profile that map to the job's \
  requirements. Prefer specifics over adjectives.
- No clichés. Do NOT open with "I am writing to express my interest" or similar.
- Do not fabricate. Only use facts that are in the candidate profile.
- Do not invent the hiring manager's name or the exact company address. If unknown, open \
  with a simple greeting like "Dear Hiring Team,".
- Output Markdown only — no code fences, no meta commentary."""
