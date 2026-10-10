# Worked examples — input → triage → decision

Ten cases covering every decision (`merge_into`, `ask_student`, `file_new`,
`reject`), both question languages and all four severities. Rules live in
[../SKILL.md](../SKILL.md); the bucket table in [buckets.md](buckets.md).
A filed or merged result must always pass
`python scripts/triage_check.py '<result json>'`.

## 1. Hinglish duplicate → merge, escalated

- **Student:** "aaj lunch mein dal mein keeda tha" (+ photo)
- **Triage:** Mess / Hygiene → Mess Committee · meal `lunch` (inferred from
  "aaj lunch mein") · severity `urgent` (insects in food, photo confirms)
- **Summary:** "Insects found in food at lunch"
- **Decision:** `find_similar` returned open #14 "Insects found in food at lunch"
  — same category, same (only) mess, same meal → **`merge_into 14`**.
  5th report → escalated, jumps to #1 on the board. No question asked:
  everything needed was inferable.

## 2. Vague location → ask once, then file

- **Student:** "AC se paani tapak raha hai"
- **Triage:** Hostel / Electrical & AC → Hostel Office · `building` and `spot`
  missing — a technician cannot walk to "the AC"
- **Decision:** **`ask_student`**, one Hinglish sentence for BOTH fields at once:
  *"Kaunsa hostel aur room number?"* (reason: missing_fields)
- **Student answers:** "BH2 (Gopad), E207"
- **Result:** severity `high`, summary "Water leaking from AC in room E207" →
  **`file_new`** in the Hostel Office queue. (1 of the 2 allowed questions used.)

## 3. Nonsense → reject

- **Student:** "the moon is too bright tonight"
- **Decision:** **`reject`** with a polite reason: "Sorry, this isn't a campus
  facility problem — report a hostel, mess, IT, academic or campus issue and we'll
  route it to the right office." No bucket, nothing public.

## 4. English duplicate, different words → merge

- **Student:** "internet is down in BH1 again tonight"
- **Triage:** IT / Wi-Fi & LAN → IT Cell · building `BH1 (Kanhar)` · severity `high`
  (no Wi-Fi blocks daily life)
- **Summary:** "No Wi-Fi in BH1 (Kanhar)"
- **Decision:** `find_similar` returned open #8 "No Wi-Fi on 3rd floor of BH1" —
  same category, same building, same building-wide issue → **`merge_into 8`**.
  Different wording, same problem: that is what dedupe is for.

## 5. Same building, different room → file, do NOT merge

- **Student:** "my study chair is broken, seat came off (F101)"
- **Triage:** Hostel / Furniture & Doors → Hostel Office · building
  `BH2 (Gopad)` · spot `F101` · severity `medium`
- **Summary:** "Study chair broken in room F101"
- **Decision:** `find_similar` returned open #21 "Broken chair in room F105" —
  same category and building, but a different room can be a different broken
  chair → **`file_new`**. Two chairs are not one complaint.

## 6. Same spot possibly already reported → ask a disambiguation question

- **Student:** "2nd floor washroom ka tap phir se leak kar raha hai"
- **Triage:** Hostel / Plumbing & Water → Hostel Office · building
  `BH2 (Gopad)` · spot "2F washroom" · severity `medium`
- **Decision:** `find_similar` returned open #31 "Tap leaking in 2F washroom" —
  same category, same building, but "phir se" could mean the same tap was not
  fixed or a second tap → **`ask_student`** (reason: ambiguous_duplicate), one
  question naming the candidate: *"Ye BH2 (Gopad) ki 2F washroom wala tap hai jo
  #31 mein report hai, ya koi doosra?"* (1 of 2 questions used.)

## 7. No bucket fits → Other with a suggested category

- **Student:** "kapde dhulne ki koi suvidha nahi hai hostel mein"
- **Triage:** Other → Admin · severity `low` · suggested_category `Laundry`
- **Summary:** "No laundry facility in hostel"
- **Decision:** **`file_new`**. Admin's Other panel groups it under "Laundry"
  (3 reports → a promotion candidate). Never invent a 16th bucket.

## 8. Safety risk now → urgent, file

- **Student:** "there's a live wire sparking in the E-wing ground corridor of BH2"
- **Triage:** Hostel / Electrical & AC → Hostel Office · building
  `BH2 (Gopad)` · spot "E-wing ground corridor" · severity `urgent`
  (sparking/exposed wires = safety risk now)
- **Summary:** "Live wire sparking in BH2 ground corridor"
- **Decision:** no open duplicate → **`file_new`** in the Hostel Office queue.

## 9. Suggestion → low severity, nothing to ask

- **Student:** "please add more salad and curd to the mess menu"
- **Triage:** Mess / Service & Timings → Mess Committee · severity `low`
  (a suggestion) · building auto-filled `Mess`, never asked for
- **Summary:** "Menu suggestion: more salad and curd at mess"
- **Decision:** **`file_new`**. This bucket needs no required fields, so no
  question is asked even though the student gave no location.

## 10. New washroom issue → place-word spot, file

- **Student:** "3rd floor Academic Building washroom ka tap toota hai"
- **Triage:** Academic / Classrooms & Labs → Academic Office · building
  `Academic Building` · spot "3rd floor washroom" · severity `medium`
- **Summary:** "Tap broken in 3rd-floor Academic Building washroom"
- **Decision:** no open duplicate → **`file_new`**. The spot is a place
  ("3rd floor washroom"), not a room code — that is still walkable, so it
  passes; "my room" or "upstairs" would not.

## Patterns these examples teach

- Missing required fields → ONE question, all fields together, student's language.
- Same category + same building + same spot (or same building-wide issue) → merge.
- Same category + same building, different room → file separately.
- Photos can raise severity (example 1), never lower it.
- Priority and escalation are computed in code, never guessed.
