# Rules for AI coding tools

**Read `docs/BRIEF.md` first.** It is the single source of truth. `CLAUDE.md` has the
ownership table and the short version of these rules.

This is a hackathon project (OpenLake x MLH Hack Day, IIT Bhilai, 10 Oct 2026) that uses
Gemma 4 through the Gemini API.

## Key safety — never break these

- Use the `google-genai` package (`from google import genai`) and the helper in `gemma_client.py`.
- The model is `gemma-4-26b-a4b-it`. Do not switch to another model or another AI provider.
- Never hard-code an API key. Read it from the environment (`GEMINI_API_KEY`, loaded from `.env`).
- Never print an API key, not even partially, and never put one in a commit, an issue or a log.
- Keep `.env` out of git. Keep the `LICENSE` file (MIT).
- If unsure about the Gemma API, read https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api
  or write a 10-line probe and run it. Do not guess.

## Project rules

- Go through `gemma_client.py` for every model call. It handles call spacing, 429/500
  retries, the on-disk cache and the usage counter. Do not call `genai` directly.
- Go through `api/db.py` for every SQL statement. No SQL anywhere else.
- A complaint costs **2 Gemma calls**: one to pick a bucket and look for duplicates, one to
  decide. If you find yourself making a third, the harness is being used wrong.
- Gemma never computes priority, escalation or ids. Code does:
  `priority = report_count x {urgent:4, high:3, medium:2, low:1}`,
  `escalated = report_count >= 5 or severity == "urgent"`.
- Limits are enforced in code, not asked of the model: max 2 questions per report;
  `merge_into` only accepts an id that came back from the last `find_similar`.
- Tools learn the current report (thread id, raw text, photo path) from `contextvars`, set by
  `complaints/agent.py`. Never make Gemma pass an id it could hallucinate.
- `@tool` parameters can only be `str`, `int`, `float`, `bool`. Use flat params; pass `""` for unknown.
- `run_tool` always returns text. Errors come back as text starting with `Error`.
- Keep `python -m pytest harness` green. New harness behaviour needs a test using the
  fake `generate` pattern already in `harness/test_agent.py`.
- Keep `README.md` current: the model name, the line of code that calls it, how to run, a screenshot.
- `python tools/check_submission.py` must show no FAIL before we submit.

## Scope

- No login system. No deployment. No real emails, SMS or WhatsApp.
- Photos stay on local disk in `uploads/` (gitignored) and are visible only in the Authority view.
- Do not add a shell tool or an arbitrary-network tool to the harness.

## Superseded starter defaults

The starter's AGENTS.md said "one screen, one Gemma call per click, no database, tools only
in `notes/`". Those were beginner defaults for a single-file demo. This project is a real
multi-agent app: it has a database (`api/db.py`), a multi-step harness loop, and tools that
read and write complaints. The key-safety rules above still apply without exception.
