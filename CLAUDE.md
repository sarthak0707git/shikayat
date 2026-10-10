# Read `docs/BRIEF.md` before anything.

It is the single source of truth for this project. If the code or the API behaves
differently from the brief, trust reality, tell your human, and adapt.

## What this is

**Shikayat** — campus complaints that count. A student writes a complaint in English,
Hinglish or Hindi (optionally with a photo). **Gemma 4** (`gemma-4-26b-a4b-it`, via the
Gemini API) buckets it, summarises it, checks whether it is already open, merges
duplicates, and **asks the student back** when something an authority needs is missing.
A public board ranks issues by priority. Each authority sees only its own queue.

## Who owns what — stay inside your folders

| Path | Owner | GitHub |
|---|---|---|
| `harness/`, `complaints/`, `api/` | P1 | @sarthak0707git |
| `web/` (shell, design system, Report, Board, Authority) | P2 | @xtacy-on-code |
| `seed/` (`complaints.json`, `test_cases.json`, `validate_seed.py`) | P3 | @sumagnadas |
| `skills/campus-complaint-triage/` | P4 | @DeathSlash945 |
| `tools/check_shikayat.py`, `README.md`, `LICENSE`, `demo/`, PPT | P5 | @Neil-ctrl |
| `docs/BRIEF.md`, `CLAUDE.md`, `AGENTS.md` | P1 | ask before editing |

Section 6 of the brief (the API contract) changes only by P1 telling P2.

## Non-negotiables

- Model is `gemma-4-26b-a4b-it` through the Gemini API (`google-genai`). Never another model or provider.
- Never hard-code or print the API key. It lives in `.env`, which is gitignored.
- `git pull --rebase` before every push. Short commit messages.
- Never leave `main` broken for more than one step.
- Verify, don't guess: if unsure how the Gemma API behaves, write a 10-line probe and run it.
- No login system, no deployment, no real emails/SMS/WhatsApp.

## Adjustments to the brief (reality, decided 10 Oct ~14:10)

1. **Real buildings.** `BH1 (Kanhar)`, `BH2 (Gopad)`, `GH1 (Indravati)`,
   `MSH (Married Hostel)`, `Mess`, `Academic Building`.
2. **One common mess** on campus. So `building` is auto-filled `"Mess"` for Mess
   categories and dropped from their `required_fields` — Food Quality and Hygiene
   require `meal` only. Otherwise Gemma pointlessly asks "which mess?". The column
   stays in the DB and the API, so the section 6 contract is unchanged.
3. **Rooms have wings.** A `spot` for an in-room issue is a wing letter + number:
   `E207`, `B322`, `F101`. For shared spaces: `2F washroom`, `E-wing ground corridor`.
   "my room" or "upstairs" is NOT enough.
4. **Demo script** reads `Mess` (not "Mess A") and the vague AC report resolves to
   `BH2 (Gopad)` / `E207` (not "H2 214").

## How to run

```bash
./.venv/bin/python -m api.seed --reset          # load seed data into data/shikayat.db
./.venv/bin/uvicorn api.main:app --reload       # API on :8000
cd web && npm run dev                           # Vite on :5173, proxies /api
./.venv/bin/python -m complaints.cli "aaj dal mein keeda tha"   # one report, in the terminal
./.venv/bin/python -m pytest harness            # harness tests (no key, no internet)
```
