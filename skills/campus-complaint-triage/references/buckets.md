# Buckets, places and rules — canonical table

**Keep in sync with** `../scripts/triage_check.py` (`CATEGORIES`) and
`complaints/categories.py` (`CATEGORIES`). One common mess on campus, so Mess
categories never require a `building` (it is auto-filled `"Mess"`).

## The 15 buckets

| Domain | Category | Required fields | Authority |
|---|---|---|---|
| Hostel | Electrical & AC | building, spot | Hostel Office |
| Hostel | Plumbing & Water | building, spot | Hostel Office |
| Hostel | Furniture & Doors | building, spot | Hostel Office |
| Hostel | Housekeeping | building, spot | Hostel Office |
| Mess | Food Quality | meal | Mess Committee |
| Mess | Hygiene | meal | Mess Committee |
| Mess | Service & Timings | (nothing) | Mess Committee |
| IT | Wi-Fi & LAN | building, spot | IT Cell |
| IT | Portals & Accounts | (nothing) | IT Cell |
| Academic | Classrooms & Labs | building, spot | Academic Office |
| Campus | Water Coolers | spot | Estate Office |
| Campus | Roads & Lights | spot | Estate Office |
| Campus | Transport | spot | Transport Cell |
| Campus | Animals & Safety | spot | Estate Office |
| Other | Other | (nothing) + `suggested_category` | Admin |

Anything that fits no bucket is filed as `Other` with a `suggested_category`
(e.g. "Laundry", "Gym").

## Buildings — the only legal values of `building`

- `BH1 (Kanhar)`
- `BH2 (Gopad)`
- `GH1 (Indravati)`
- `MSH (Married Hostel)`
- `Mess`
- `Academic Building`

Academic rooms are not named more specifically than "Academic Building".
Mess categories take `building = "Mess"` automatically and do not ask for it.

## `spot` — walkable by a technician, or it is not a spot

Valid (one of):

- wing + room: `E207`, `B322`, `F101` (regex `^[A-Z]\d{3}$`)
- a floor/place description containing one of
  `floor`, `F`, `washroom`, `corridor`, `lobby`, `gate`, `ground`:
  `2F washroom`, `E-wing ground corridor`, `3rd floor lobby`, `main gate`

Not valid: `my room`, `upstairs`, `here`, `214`, `Room 214` (no wing).

## `meal` — `breakfast | lunch | snacks | dinner`

Inferable from time words: "aaj lunch mein dal mein keeda tha" → `lunch`.

## Severity rubric

- **urgent** — safety or health risk now: sparking/exposed wires, gas smell, flooding,
  no water for a whole hostel, insects or foreign objects in food, several people sick
  after a meal.
- **high** — blocks daily life: no Wi-Fi on a floor, AC/fan dead, broken door lock,
  undercooked food.
- **medium** — annoying but workable: dirty washroom, slow Wi-Fi, broken chair.
- **low** — cosmetic or a suggestion: paint, menu requests.

A photo can raise severity (an insect visible in the plate → urgent). It never lowers it.

## Summary rules

English, neutral, ≤ 12 words, **no personal names** (it is shown publicly).
Good: "Tap leaking in 2nd-floor washroom". Bad: "Rahul's fan is broken again".

Priority and escalation are computed in code, never by the model:
`priority = report_count × (urgent 4 | high 3 | medium 2 | low 1)`,
`escalated = report_count >= 5 or severity == urgent`.

## Check a triage result

```bash
python scripts/triage_check.py '{"category":"Electrical & AC","building":"BH2 (Gopad)","spot":"E207","severity":"high","summary":"AC leaking water in room E207"}'
python scripts/triage_check.py result.json     # a JSON file
python scripts/triage_check.py -               # JSON from stdin
```

Prints one `PASS`/`FAIL` line per check, then `OK` or `FAILED` (exit 1 on any FAIL).
