---
name: campus-complaint-triage
description: Triage a Shikayat campus complaint (IIT Bhilai) end to end - extract building, spot and meal from raw English/Hinglish/Hindi text, pick one of the 15 fixed buckets (domain and authority), apply the severity rubric, write a neutral English summary of at most 12 words with no personal names, compare against open complaints, then file, merge, ask the student back or reject. Use when classifying, deduplicating or validating a student complaint report.
license: MIT
metadata:
  author: DeathSlash945
  project: shikayat
  version: "1.0"
---

# Campus complaint triage

Shikayat turns one student report (English, Hinglish or Hindi, optional photo) into a
bucketed, deduplicated complaint. Work through the steps below in order. Some limits
here are enforced in code (at most 2 questions, field size limits) — respect them
instead of testing them.

## 0. Check your triage result

This skill ships a validator (Python stdlib only). Run it on the JSON triage result
before you trust it:

```bash
python skills/campus-complaint-triage/scripts/triage_check.py \
  '{"category":"Electrical & AC","building":"BH2 (Gopad)","spot":"E207","severity":"high","summary":"AC leaking water in room E207"}'
```

It prints one `PASS`/`FAIL` line per check and then `OK` or `FAILED` (exit 1 on any
FAIL). It also accepts a JSON file path, or `-` to read the same JSON from stdin.

## 1. Extract the fields

- `building` — one of the six real IIT Bhilai names below. For Mess categories it is
  auto-filled `"Mess"` and must never be asked for.
- `spot` — walkable by a technician: wing + room (`E207`) or a place
  (`2F washroom`, `E-wing ground corridor`). `my room`, `upstairs`, `214` are NOT enough.
- `meal` — `breakfast | lunch | snacks | dinner`; infer from time words
  ("aaj lunch mein" → lunch).
- `severity` — the rubric in §3.
- `summary` — English, neutral, ≤ 12 words, **no personal names** (it is public).
- `details` — English, 1–2 sentences; include what the photo shows if there is one.

## 2. Pick the bucket (exactly these 15)

| Domain | Authority | Categories (required fields) |
|---|---|---|
| Hostel | Hostel Office | Electrical & AC, Plumbing & Water, Furniture & Doors, Housekeeping — all need `building` + `spot` |
| Mess | Mess Committee | Food Quality and Hygiene need `meal`; Service & Timings needs nothing |
| IT | IT Cell | Wi-Fi & LAN needs `building` + `spot`; Portals & Accounts needs nothing |
| Academic | Academic Office | Classrooms & Labs needs `building` + `spot` |
| Campus | Estate Office | Water Coolers, Roads & Lights, Animals & Safety need `spot` |
| Campus | Transport Cell | Transport needs `spot` |
| Other | Admin | Other needs nothing; add a `suggested_category` (e.g. "Laundry") |

Legal `building` values: `BH1 (Kanhar)`, `BH2 (Gopad)`, `GH1 (Indravati)`,
`MSH (Married Hostel)`, `Mess`, `Academic Building`.

The canonical one-row-per-bucket table lives in
[references/buckets.md](references/buckets.md) — it is the source of truth for
`scripts/triage_check.py` and `complaints/categories.py`. Read it when in doubt.

## 3. Severity rubric

- **urgent** — safety or health risk now: sparking/exposed wires, gas smell, flooding,
  no water for a whole hostel, insects or foreign objects in food, several people sick
  after a meal.
- **high** — blocks daily life: no Wi-Fi on a floor, AC/fan dead, broken door lock,
  undercooked food.
- **medium** — annoying but workable: dirty washroom, slow Wi-Fi, broken chair.
- **low** — cosmetic or a suggestion: paint, menu requests.

A photo can raise severity (insect visible in the plate → urgent). It never lowers it.

## 4. Find duplicates, then decide

Call `find_similar` first with what you extracted, then **exactly one** of:

1. Not a campus problem, gibberish, abuse or a test → `reject` with a polite reason.
2. Required fields missing → `ask_student` for **all** of them in **one** question
   ("Kaunsa hostel aur room number?").
3. Same category + same building + same spot (or the same building-wide issue) → `merge_into`.
4. Same category + same building, but the spot is unclear or could be a different
   instance → `ask_student` one disambiguation question that names the candidate:
   "Is this the 2F washroom tap already reported, or a different one?"
5. Otherwise → `file_new`.

**Limits enforced in code:** at most **2** questions per report; after the 2nd,
`ask_student` errors, so decide with what you have — `file_new` is then allowed with
missing fields and the complaint is marked `needs_details`. `merge_into` only accepts
an id that came back from the last `find_similar`.

Priority and escalation are computed in code, never by you:
`priority = report_count × (urgent 4 | high 3 | medium 2 | low 1)`,
`escalated = report_count >= 5 or severity == urgent`.

## 5. Style

- Questions to the student: their own language and tone (Hinglish in → Hinglish out),
  one short sentence.
- `summary`: English, neutral, ≤ 12 words, no personal names — it is shown publicly.
- Never surface the raw message, photo or anyone's name on the public board.

## 6. Worked examples (more in [references/examples.md](references/examples.md))

**Hinglish duplicate → merged.** "aaj lunch mein dal mein keeda tha" + photo.
Mess / Hygiene, meal `lunch` (inferred from "aaj lunch mein"), severity `urgent`
(insects in food; the photo confirms). `find_similar` already shows "Insects found
in food at lunch" — same category, same mess, same meal → `merge_into`. The count
goes up; no question is asked because nothing was missing.

**Vague location → one question.** "AC se paani tapak raha hai". Hostel /
Electrical & AC, but `building` and `spot` are missing, so ask once, in Hinglish,
for **both**: *"Kaunsa hostel aur room number?"* The answer "BH2 (Gopad), E207"
completes the triage: severity `high`, summary "Water leaking from AC in room E207",
`file_new`. That was 1 of the 2 allowed questions.

**Nonsense → reject.** "the moon is too bright tonight". Not a campus facility
problem → `reject` with one polite sentence ("Sorry, this isn't a campus facility
problem — report a hostel, mess, IT, academic or campus issue and we'll route it").
No bucket, nothing public.

## Files

- [references/buckets.md](references/buckets.md) — full bucket table, buildings,
  spot/meal/severity examples, summary rules.
- [references/examples.md](references/examples.md) — 10 worked examples:
  input → category, severity, summary, decision.
- [scripts/triage_check.py](scripts/triage_check.py) — the validator above,
  stdlib only, no dependencies.
