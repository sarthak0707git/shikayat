# BRIEF — "Shikayat": campus complaints that count

Working name, rename freely. OpenLake × MLH Hack Day, IIT Bhilai, Sat 10 Oct 2026, all times IST.
Submission closes 17:00 on OrganizerHQ. **We submit by 16:40.** Feature freeze **15:50**.
Judging: works in demo 30 · useful idea 25 · use of Gemma 4 20 · creativity 15 · clear demo 10.
We enter BOTH MLH challenges: Best Use of Gemma 4 and Best Open-Source AI Project.

Every Claude Code session on this team reads this file first. It is the single source of truth.
If the code or the API behaves differently from what this file says, trust reality, tell your human, and adapt.
Only Person 2 edits section 6 (the contract). Everyone else asks.

---

## 1. The product in one paragraph

A student writes a campus complaint any way they like (English, Hinglish, Hindi), optionally with a photo.
Gemma 4 reads it, puts it in a predefined bucket (domain → category), writes a neutral one-line summary,
and checks whether the same issue is already open. If it is, the report is merged and the count goes up.
If the complaint is missing something an authority needs (e.g. an AC leak with no room number) or Gemma
cannot tell whether it is a duplicate, Gemma **asks the student back** before deciding.
A public board shows which issues most students are hitting, with clean charts ranked by priority.
Each authority (Hostel Office, Mess Committee, IT Cell, ...) sees only its domain's queue and marks issues
in progress or resolved.

Pitch line: *"Complaint portals already exist. They make you fill forms and bury wardens in duplicates.
Ours takes a Hinglish rant or a photo, works out whether it's already been reported, and asks back when it's unsure."*

## 2. Demo script (90 seconds) — everything we build serves this

1. **Board.** "Mess hygiene and Hostel water are the top priorities this week" — charts + ranked cards.
2. **Live report, Hinglish + photo:** "aaj lunch mein dal mein keeda tha" + photo → Gemma: Mess · Hygiene · urgent,
   asks nothing because it can infer the meal → merged into the existing "Hygiene issues in Mess A food" complaint →
   the photo raises it to urgent, it's the 5th report → **escalated**, and it jumps to #1 on the board.
3. **Live report, vague:** "AC se paani tapak raha hai" → Gemma asks *"Kaunsa hostel aur room number?"* →
   "H2 214" → filed as a new complaint in the Hostel Office queue.
4. **Authority view.** Switch to Mess Committee → escalated complaint with all reports and photos → mark In progress
   → public board shows the new status.
5. **If a judge types nonsense** ("the moon is too bright") → polite "not a campus issue" rejection.

## 3. Architecture

```
React (Vite)  ──/api──▶  FastAPI (api/)  ──▶  complaints/agent.py  ──▶  harness/Agent  ──▶  Gemma 4 (Gemini API)
     ▲                       │                       │ tools
     └──── JSON ─────────────┤                       ▼
                             └──▶ SQLite (data/shikayat.db) ◀── complaints/tools.py (via api/db.py)
photos: uploads/<uuid>.jpg (served at /uploads/...)
```

- Python backend in the repo root, built on the official starter (gemma_client.py + harness/).
- Model: `gemma-4-26b-a4b-it` (fast MoE). Do not switch models or providers.
- Storage: SQLite via the standard `sqlite3` module. Photos on local disk in `uploads/`.
- One demo laptop runs everything. No deployment needed.

### Repo layout and ownership

| Path | Owner | What |
|---|---|---|
| `harness/` | P1 | Starter harness + our upgrades (section 5). Keep existing tests passing. |
| `complaints/` | P1 | `categories.py`, `prompt.py`, `tools.py`, `agent.py`, `cli.py`, `eval.py` |
| `api/` | P2 | `main.py` (FastAPI), `db.py` (all SQL), `seed.py` |
| `web/` | P3 + P4 | Vite React app. P3 owns shell, design system, Report page. P4 owns Board + Authority pages. |
| `seed/` | P5 | `complaints.json`, `test_cases.json` |
| `skills/campus-complaint-triage/` | P5 | Agent skill (Agent Skill Open Standard) |
| `README.md`, `docs/`, `LICENSE`, `demo/` | P5 | Submission material |
| `docs/BRIEF.md` (this), `CLAUDE.md`, `AGENTS.md` | P2 | Shared rules |

## 4. Gemma's job (the rules) — P1 implements in `complaints/prompt.py`

### 4.1 Buckets (`complaints/categories.py`, mirrored into the `categories` DB table at startup)

| Domain | Category | Required fields | Authority |
|---|---|---|---|
| Hostel | Electrical & AC | building, spot | Hostel Office |
| Hostel | Plumbing & Water | building, spot | Hostel Office |
| Hostel | Furniture & Doors | building, spot | Hostel Office |
| Hostel | Housekeeping | building, spot | Hostel Office |
| Mess | Food Quality | building, meal | Mess Committee |
| Mess | Hygiene | building, meal | Mess Committee |
| Mess | Service & Timings | building | Mess Committee |
| IT | Wi-Fi & LAN | building, spot | IT Cell |
| IT | Portals & Accounts | (none) | IT Cell |
| Academic | Classrooms & Labs | building, spot | Academic Office |
| Campus | Water Coolers | spot | Estate Office |
| Campus | Roads & Lights | spot | Estate Office |
| Campus | Transport | spot | Transport Cell |
| Campus | Animals & Safety | spot | Estate Office |
| Other | Other | (none) | Admin |

- `building` = hostel / mess / block name from `BUILDINGS` in categories.py. **The team fills in the real IIT Bhilai names** (placeholders until then: "Hostel 1".."Hostel 4", "Mess A", "Mess B", "Academic Block", "Library").
- `spot` = specific enough for a technician to walk to: "Room 214" for in-room issues, "2F washroom" / "ground-floor corridor" for shared spaces. "my room" or "upstairs" is NOT enough.
- `meal` = breakfast | lunch | snacks | dinner. Gemma may infer it from time words ("aaj lunch mein").
- **New types of complaint:** anything that fits no category is filed as `Other` with a `suggested_category`
  (e.g. "Laundry"). The Admin view groups Other complaints by suggestion and can promote one to a real category
  (stretch). Categories are read from the DB each run, so a promoted category works immediately with no code change.

### 4.2 Severity rubric

- **urgent** — safety or health risk now: sparking/exposed wires, gas smell, flooding, no water for a whole hostel, insects or foreign objects in food, several people sick after a meal.
- **high** — blocks daily life: no Wi-Fi on a floor, AC/fan dead, broken door lock, undercooked food.
- **medium** — annoying but workable: dirty washroom, slow Wi-Fi, broken chair.
- **low** — cosmetic or a suggestion: paint, menu requests.
A photo can raise severity (an insect visible in the plate → urgent). It never lowers it.

### 4.3 Decision rule (code enforces the limits, Gemma decides within them)

For each report, Gemma first calls `find_similar` with what it extracted, then calls exactly ONE of
`file_new`, `merge_into`, `ask_student`, `reject`:

1. Not a campus problem, gibberish, abuse, or a test → `reject` with a polite reason.
2. Required fields missing (the `find_similar` result lists them) → `ask_student` for ALL missing fields in one question.
3. A candidate has the same category + same building + same spot (or the same building-wide issue) → `merge_into`.
4. Same category + same building, but the spot is unclear or could be a different instance → `ask_student` one
   disambiguation question that names the candidate: *"Is this the 2F washroom tap already reported, or a different one?"*
5. Otherwise → `file_new`.

Limits enforced in code: at most **2** questions per report. After 2, `ask_student` returns an error and Gemma
must decide with what it has; `file_new` is then allowed with missing fields and the complaint is marked
`needs_details`.

### 4.4 Output style

- Questions to the student: same language and tone the student used (Hinglish in → Hinglish out), one short sentence.
- `summary`: English, neutral, ≤ 12 words, no personal names (it is shown publicly). e.g. "Tap leaking in 2nd-floor washroom".
- `details`: English, 1–2 sentences, includes what the photo shows if there is one.
- Inject today's date, weekday and time (IST) into the prompt so "aaj", "kal raat" resolve correctly.

## 5. Harness upgrades — P1 (this is our original work for the open-source track)

The starter's `Agent.run(question)` is text-only, stateless, sends every registered tool, and always needs an
extra model round to finish. We change it so a complaint takes **2 Gemma calls**, not 4. Keep `run()` working
exactly as before for old callers and keep `python -m pytest harness` green; add tests with the fake `generate`.

1. **Per-agent tool sets:** `Agent(tools=["find_similar", ...])` sends only those declarations (default: all).
2. **Image input:** `run_task(question, image_path=None)` adds the image as a Part. Try inline bytes
   (`types.Part.from_bytes(data=..., mime_type=...)`) first; inline images are not documented for Gemma on the API,
   so probe it. Fallback: `client.files.upload` (what `gemma_client.ask_with_image` does).
3. **Terminal tools:** `@tool(stop=True)`. A call that does not return text starting with "Error" ends the run
   immediately and returns its result. No extra "final answer" round.
4. **Pause for a human:** `@tool(pause=True)`. The run returns `RunResult(status="needs_input", question=..., state=...)`.
   `Agent.resume(state, answer)` appends the answer as a user turn and continues the same conversation.
   State lives in an in-memory dict keyed by `thread_id` (fine for a demo; say so in the README).
5. **Step log for the UI:** keep `steps`, and add a friendly `label` per step ("Looking for similar reports in Hostel 2").
6. `RunResult` = `{status: done|needs_input|stopped|error, tool: name|None, result: str, question: str|None, steps: [...], state}`.

Starter facts to respect:
- `@tool` inputs can only be `str`, `int`, `float`, `bool`. Use flat params; pass "" for unknown.
- `run_tool` always returns text; errors come back as text starting with "Error".
- `gemma_client.MIN_SECONDS_BETWEEN_CALLS` defaults to **4 s between calls**. Lower it in `.env` to what your real
  limits allow (check aistudio.google.com/rate-limit). Rate limits are **per Google Cloud project**: every person
  uses their own key while building; keep one fresh key for the demo.
- Tools need to know the current report (thread id, raw text, photo path). Pass it with `contextvars`, set by
  `complaints/agent.py` before the run. Never make Gemma pass ids it could hallucinate.
- The starter's `AGENTS.md` says "one Gemma call per click, no database, tools only in notes/". Those are beginner
  defaults; P2 rewrites AGENTS.md to match this brief (keep its key-safety rules).

### 5.1 Tools (`complaints/tools.py`)

| Tool | Params | Kind | Does |
|---|---|---|---|
| `find_similar` | category, building, spot, meal (str) | normal | Returns JSON text: `required_fields`, `missing_fields`, and up to 5 open complaints in that category (+ building if given): id, summary, building, spot, report_count, last_reported_at |
| `file_new` | category, building, spot, meal, severity, summary, details, language, suggested_category (str) | stop | Validates category/severity and required fields (errors if missing and < 2 questions asked), creates complaint + report |
| `merge_into` | complaint_id (int), severity (str), reason (str), details (str) | stop | Errors if the id was not in the last `find_similar` result. Adds the report, bumps count, keeps the highest severity seen |
| `ask_student` | question (str), reason (str: missing_fields \| ambiguous_duplicate) | pause | Errors after 2 questions |
| `reject` | reason (str) | stop | Records a rejected report, nothing public |

Escalation and priority are computed in code, never by Gemma:
- `priority = report_count × weight`, weights urgent 4, high 3, medium 2, low 1.
- `escalated = report_count >= 5 or severity == "urgent"`.

`complaints/cli.py`: `python -m complaints.cli "AC se paani aa raha hai" --photo demo/photos/ac.jpg` runs one report
and prompts for answers in the terminal. `complaints/eval.py` runs `seed/test_cases.json` and prints a pass/fail table.

## 6. API contract — P2 owns; frontends build against it from minute one

Base: FastAPI on port 8000. Vite dev server proxies `/api` and `/uploads` to it. CORS allow the Vite origin.
All times ISO 8601 with +05:30. Display dates as `DD MMM YYYY`, times as `h:mm a`.

```
POST  /api/report                   multipart: text (str), photo (file, optional)       → ReportResult
POST  /api/report/{thread_id}/answer  json {"answer": "H2 214"}                          → ReportResult
GET   /api/complaints?domain=&authority=&status=&sort=priority|recent                  → Complaint[]
GET   /api/complaints/{id}                                                              → ComplaintDetail
PATCH /api/complaints/{id}          json {"status": "in_progress|resolved|open", "note": "..."} → Complaint
GET   /api/stats?domain=                                                                → Stats
GET   /api/categories                                                                   → Category[]
POST  /api/categories               json {"name","domain","authority","required_fields":[]} → Category   (stretch)
GET   /api/health                                                                       → {"ok": true}
GET   /uploads/<file>                                                                   → image
```

```json
// ReportResult
{
  "thread_id": "t_8f2a1c",
  "status": "merged",                       // filed | merged | needs_input | rejected | error
  "message": "Added to #14. You're the 5th student to report this.",
  "question": null,                         // set when status = needs_input
  "complaint": { /* Complaint */ },         // null for needs_input / rejected / error
  "steps": [ { "kind": "tool_call", "label": "Looking for similar reports in Mess A" } ]
}

// Complaint (public board shows only these fields — never raw text, photos or names)
{
  "id": 14, "domain": "Mess", "category": "Hygiene", "authority": "Mess Committee",
  "building": "Mess A", "spot": null, "meal": "lunch",
  "summary": "Insects found in food at lunch",
  "severity": "urgent", "status": "open", "escalated": true, "needs_details": false,
  "report_count": 5, "priority": 20, "photo_count": 2,
  "first_reported_at": "2026-10-06T13:10:00+05:30", "last_reported_at": "2026-10-10T13:02:00+05:30",
  "resolution_note": null, "suggested_category": null
}

// ComplaintDetail = Complaint + authority-only fields
{ "...": "...", "reports": [ { "id": 51, "raw_text": "aaj dal mein keeda tha", "photo_url": "/uploads/3f2a.jpg",
    "created_at": "...", "merge_reason": "Same mess, same issue", "followups": [ {"q": "...", "a": "..."} ] } ] }

// Stats
{
  "kpis": { "open": 42, "reported_7d": 96, "resolved_7d": 11, "escalated": 6 },
  "by_domain": [ { "domain": "Hostel", "open": 18, "in_progress": 4, "resolved": 9 } ],
  "top_issues": [ { "id": 14, "summary": "...", "domain": "Mess", "priority": 20, "report_count": 5, "severity": "urgent", "status": "open" } ],
  "daily": [ { "date": "2026-09-27", "reports": 5 } ],          // last 14 days, oldest first
  "other_suggestions": [ { "name": "Laundry", "count": 3 } ]
}

// Category
{ "id": 1, "name": "Plumbing & Water", "domain": "Hostel", "authority": "Hostel Office", "required_fields": ["building", "spot"] }
```

### 6.1 Database (`api/db.py` owns every SQL statement)

- `categories(id, name, domain, authority, required_fields JSON)`
- `complaints(id, category, domain, authority, building, spot, meal, summary, details, severity, status, escalated, needs_details, report_count, suggested_category, first_reported_at, last_reported_at, resolved_at, resolution_note)`
- `reports(id, complaint_id NULL, thread_id, raw_text, language, photo_path, outcome, merge_reason, followups JSON, created_at)`

Functions P1's tools call (P2 writes these first; P1 uses an in-memory fake until then):
`find_open(category, building) -> list[dict]`, `create_complaint(fields) -> dict`, `add_report(complaint_id, report) -> dict`,
`create_report(report) -> dict`, `get_category(name) -> dict|None`, `list_categories() -> list[dict]`.

### 6.2 Photos

- Frontend shrinks photos to max 1280 px JPEG (canvas) before upload. Backend accepts `image/*` only, max 5 MB,
  saves `uploads/<uuid>.jpg`, stores the path. `uploads/` is gitignored; demo photos live in `demo/photos/`.
- No Google Drive: OAuth and sharing permissions cost an hour, and Gemma needs the bytes anyway.
  README note: production would use object storage (S3 / Cloud Storage).
- Photos are visible only in the Authority view.

## 7. UI — P3 + P4. "Very neat" is a requirement

App UI, calm product style (structure like Linear / Stripe dashboards; never copy their branding).
Optional, 1 minute: `npx skills add emilkowalski/skills` and
`npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend-v1"`.

- **Stack:** Vite + React + TypeScript, Tailwind, shadcn/ui (button, card, badge, tabs, select, textarea, dialog, sheet,
  skeleton, sonner), Recharts, lucide-react, react-router, `motion` for small transitions. `web/src/types.ts` mirrors section 6.
  `web/src/mock/` holds fixtures matching section 6 so pages work before the API does (flag `VITE_USE_MOCK=1`).
- **Look:** light theme (projectors wash out dark UIs). Neutral zinc palette, ONE accent (indigo-600). Inter.
  1px dividers over heavy cards, radius 10–12 px, shadow only on floating things. 4/8 px spacing grid.
  Severity colours used only for severity: urgent red-600, high orange-500, medium amber-500, low slate-400.
  Status pills: open slate, in progress blue, resolved green. `tabular-nums` on every count.
- **Bans:** no gradients, no glassmorphism, no emoji in UI, no sparkle "AI" icons everywhere, no lorem ipsum.
- **Motion:** only transform/opacity, < 300 ms, ease-out, press `scale(0.97)`, no looping animations,
  honour `prefers-reduced-motion`. Two moments worth animating: the report count bumping on merge, and bars growing on the board.
- **States:** skeletons while loading, friendly empty states, error toasts in plain words ("Gemma is busy, retrying...").
- **Phone:** the Report page must work at 390 px (judges may try it on a phone): inputs ≥ 16 px, tap targets ≥ 44 px, `100dvh`.

### Pages

- **Nav:** three tabs — Report · Board · Authority. Project name on the left.
- **Report `/` (P3):** one large textarea ("Kya problem hai? English ya Hinglish, dono chalega"), attach-photo button with
  thumbnail preview, Send. Below it a chat-style thread: the student's message → Gemma's live step labels → either
  a question bubble with a reply box, or a result card (Filed #23 / Added to #14 with the count and a "5 students
  reported this" badge / Not a campus issue). "Report another" resets.
- **Board `/board` (P4):** KPI row (Open, Reported this week, Resolved this week, Escalated) → "Top priority" horizontal
  bar chart (top 8 by priority, sorted) → by-domain stacked bar (open / in progress / resolved) → 14-day reports area chart
  → ranked list of complaint cards (summary, domain · category · place, severity dot, count badge, status pill, "last
  reported 2 h ago"). Domain filter chips at the top filter everything.
- **Authority `/authority` (P4):** "Viewing as" select (Hostel Office, Mess Committee, IT Cell, Academic Office,
  Estate Office, Transport Cell, Admin) — a demo role picker, no real login (pitch: "real version uses institute SSO").
  Queue table sorted by priority with an Escalated flag; row opens a side sheet with all raw reports, photos, follow-up
  Q&A, and buttons Start work / Mark resolved (+ note). Admin also sees the "Other" panel: suggested categories with
  counts and a "Create category" button (stretch).

## 8. Seed data and tests — P5

- `seed/complaints.json`: ~45 complaints, ~120 reports spread over **27 Sep – 10 Oct 2026**, skewed so 5–6 issues
  dominate (6–14 reports each). Mix English and Hinglish raw texts. 4 resolved, 3 in progress. 4 "Other" complaints
  (Laundry ×3, Gym ×1). The demo's "Hygiene issues in Mess A food" complaint (hair, flies) starts at severity **high**
  with **4** reports, so the live insect photo raises it to urgent, makes it the 5th report, escalates it and moves it
  to #1. No AC-leak complaint in the demo hostel, so step 3 files new.
- `api/seed.py` (P2) loads it straight into SQLite (no Gemma calls) and can reset the DB: `python -m api.seed --reset`.
- `seed/test_cases.json`: 12 cases with `text`, optional `photo`, expected `outcome` (filed | merged:<id> | ask | rejected)
  and expected `category`. Include: Hinglish duplicate, English duplicate with different wording, same issue different
  room (must NOT merge), vague location (must ask), AC leak without room (must ask), nonsense (reject), Other (Laundry),
  photo-only evidence case. P1 runs `python -m complaints.eval` and tunes the prompt until ≥ 10/12 pass.
- Take 3–4 real photos on campus today for `demo/photos/` (a leaking tap, a dirty washroom, a broken chair).

## 9. Submission — P5

- `README.md`: what it is (2 lines), screenshot `docs/screenshot.png`, a `## How to run` section, model name
  `gemma-4-26b-a4b-it` and the line of code that calls it, **"What we changed in the harness and why"** (section 5),
  architecture diagram, team, and an honest note that we used Claude Code (MLH asks teams to disclose AI tools).
- `LICENSE`: keep MIT, replace `[ORGANIZER NAME]` with the team's names.
- `skills/campus-complaint-triage/SKILL.md`: follows the Agent Skill Open Standard (agentskills.io/specification) —
  folder name = `name` (lowercase, hyphens), `description` ≤ 1024 chars, body < 500 lines; teaches any agent our buckets,
  required fields, severity rubric, dedupe and ask-back rules; long tables in `references/`. Validate with `skills-ref`
  if it installs quickly, otherwise check against the spec by hand.
- `python tools/check_submission.py` must show no FAIL. Repo public. Tick BOTH challenges in OrganizerHQ.
- Record a 90-second backup video of the demo script on the demo laptop.

## 10. Timeline (IST)

| Time | Milestone |
|---|---|
| 13:50–14:05 | P2: new public repo from the starter, this brief, CLAUDE.md, AGENTS.md, folders, push. P1: Gemma probes (inline image, 2-tool function calling, latency at 1–2 s spacing). P5: start seed data. P3/P4: read contract, plan components. |
| 14:05 | Everyone clones and starts their Claude Code session. |
| 14:30 | P2: GET endpoints serve seed data; POST /report returns a mock ReportResult. P3: app shell + design tokens pushed. |
| 14:45 | P1: `python -m complaints.cli` files / merges / asks correctly on 5 cases. |
| 15:00 | P3/P4: all three pages working on mocks. |
| 15:00–15:20 | **Integrate** real POST /report end to end. Tag `mvp`. Cut line at 15:20: drop photos, category promotion and the 14-day chart if not working. |
| 15:20–15:50 | Ask-back polish, escalation, resolve flow, eval ≥ 10/12, motion polish. |
| **15:50** | **Feature freeze.** Only bug fixes after this. |
| 15:50–16:25 | Demo laptop: `python -m api.seed --reset`, rehearse the script 3×, backup video, README screenshot, check_submission. |
| 16:25–16:40 | Submit. |

## 11. How we work (every Claude Code session)

- Work in small steps. Run it, show your human the result, commit. Never leave `main` broken for more than one step.
- `git pull --rebase` before every push. Stay inside your folders (section 3). Shared files: ask P2.
- Verify, don't guess: if unsure how the Gemma API behaves, write a 10-line probe and run it.
- Never hard-code or print the API key. `.env` stays out of git.
- No real emails, SMS or WhatsApp. No login system. No deployment.
- Ask your human at most one question at a time; decide small things yourself and say what you decided.

---

## 12. Adjustments — decided on the day (10 Oct 2026, ~14:10 IST)

The brief above is the plan. These four points are reality, agreed after checking the campus
and the team. Where they differ from the sections above, **these win**.

1. **Team split differs from section 3.** Only two people have an agentic coding harness.
   - **P1 @sarthak0707git** — `harness/`, `complaints/`, `api/` (absorbs the brief's P2 backend)
     and the generator for `seed/complaints.json`.
   - **P2 @xtacy-on-code** — all of `web/`: shell, design system, Report, Board **and** Authority.
   - **P3 @sumagnadas** — `seed/`: `complaints.json`, `test_cases.json`, `validate_seed.py`.
   - **P4 @DeathSlash945** — `skills/campus-complaint-triage/` incl. `scripts/triage_check.py`.
   - **P5 @Neil-ctrl** — `tools/check_shikayat.py`, `README.md`, `LICENSE`, `demo/`, PPT, submission.

2. **Real buildings.** `BUILDINGS = ["BH1 (Kanhar)", "BH2 (Gopad)", "GH1 (Indravati)",
   "MSH (Married Hostel)", "Mess", "Academic Building"]`. Academic rooms are not named more
   specifically than "Academic Building".

3. **One common mess.** There is a single mess on campus, so `building` is auto-filled
   `"Mess"` for the Mess domain and removed from its `required_fields`: **Food Quality** and
   **Hygiene** require `meal` only, **Service & Timings** requires nothing. This stops Gemma
   asking "which mess?" when there is only one. The `building` column stays in the DB and in
   every API response, so the section 6 contract is unchanged.

4. **Rooms have wings.** A valid `spot` for an in-room issue is a wing letter plus a room
   number: `E207`, `B322`, `F101`. For shared spaces, a walkable description:
   `2F washroom`, `E-wing ground corridor`. "my room", "upstairs", "214" alone are not enough.

5. **Demo script wording** (section 2) therefore reads `Mess` instead of "Mess A", and the
   vague AC report in step 3 resolves to `BH2 (Gopad)` / `E207` instead of "H2 214".
