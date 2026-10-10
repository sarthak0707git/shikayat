"""Generates a valid baseline seed/complaints.json. P3 replaces/expands this by hand.

    python seed/generate.py          # writes seed/complaints.json

NOTE: complaints.json has been hand-edited by P3 since this generator last ran
(raw texts rewritten for realism, spot "lecture hall LH-2"). Re-running this
script OVERWRITES those edits -- update the texts here first or edit the JSON.
"""
import json, random
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
START = datetime(2026, 9, 27, 9, 0, tzinfo=IST)
END = datetime(2026, 10, 10, 13, 0, tzinfo=IST)
random.seed(7)
H = ["BH1 (Kanhar)", "BH2 (Gopad)", "GH1 (Indravati)", "MSH (Married Hostel)"]
ROOMS = ["E207", "B322", "F101", "A114", "C208", "D305", "E112", "B201", "F304", "A227"]

def t(day_offset, hour, minute=0):
    return (START + timedelta(days=day_offset, hours=hour - 9, minutes=minute)).isoformat()

def R(text, lang, day, hour, minute=0):
    return {"raw_text": text, "language": lang, "created_at": t(day, hour, minute)}

C = []
def add(cat, summary, details, severity, status="open", building=None, spot=None, meal=None,
        reports=None, suggested=None, note=None):
    C.append({"category": cat, "building": building, "spot": spot, "meal": meal,
              "summary": summary, "details": details, "severity": severity, "status": status,
              "suggested_category": suggested, "resolution_note": note, "reports": reports})

# ---- the demo complaint: EXACTLY 4 reports, high, open (live report becomes the 5th) ----
add("Hygiene", "Hair and flies found in mess food", "Students repeatedly found hair and flies in the served food.",
    "high", building="Mess", meal="lunch", reports=[
      R("aaj dal mein makkhi thi yaar, khana nahi kha paya", "hinglish", 9, 13, 10),
      R("Found a hair in the rice at lunch today. Second time this week.", "en", 10, 13, 25),
      R("mess ke khane me kal bhi baal mila tha", "hinglish", 11, 13, 5),
      R("Flies all over the serving counter at lunch.", "en", 12, 13, 40)])

# ---- the other dominant issues ----
add("Plumbing & Water", "No water supply on 3rd floor since morning", "Taps on the third floor have been dry since early morning.",
    "high", building="BH1 (Kanhar)", spot="3F washroom", reports=[
      R("bhai 2 din se paani nahi aa raha 3rd floor pe", "hinglish", 3, 8),
      R("No water in 3F washroom again today.", "en", 4, 9, 20),
      R("paani ka problem solve nahi hua abhi tak", "hinglish", 5, 10),
      R("Third floor taps completely dry since 6am.", "en", 6, 8, 15),
      R("still no water, kaise nahaye", "hinglish", 7, 9),
      R("paani nahi hai bhai, kuch karo", "hinglish", 9, 9, 45)])
add("Wi-Fi & LAN", "Wi-Fi down on 2nd floor of hostel", "No connectivity on the second floor for several days.",
    "high", building="BH2 (Gopad)", spot="2F corridor", reports=[
      R("wifi dead on 2nd floor since morning", "hinglish", 2, 11),
      R("Cannot connect to campus Wi-Fi from my room at all.", "en", 3, 14),
      R("internet nahi chal raha, assignment submit karna hai", "hinglish", 4, 20),
      R("2nd floor wifi still down.", "en", 5, 10),
      R("wifi ka kuch karo yaar, 5 din ho gaye", "hinglish", 7, 22),
      R("No Wi-Fi signal on second floor corridor.", "en", 9, 16)])
add("Housekeeping", "Washrooms not cleaned for several days", "Shared washrooms on two floors have gone uncleaned.",
    "medium", building="GH1 (Indravati)", spot="2F washroom", reports=[
      R("washroom 3 din se saaf nahi hua", "hinglish", 5, 8),
      R("The common washroom is filthy.", "en", 6, 9),
      R("safai nahi ho rahi bathroom me", "hinglish", 8, 8, 30),
      R("Washroom still dirty, no cleaning staff seen.", "en", 9, 10),
      R("bathroom ki halat kharab hai", "hinglish", 10, 8, 45),
      R("Please get the washrooms cleaned.", "en", 12, 11)])
add("Food Quality", "Undercooked rotis served at dinner", "Rotis served at dinner were raw in the middle.",
    "high", building="Mess", meal="dinner", reports=[
      R("roti kacchi thi dinner me", "hinglish", 4, 20),
      R("Dinner rotis were completely undercooked.", "en", 5, 20, 15),
      R("aaj bhi roti kacchi", "hinglish", 7, 20, 30),
      R("Raw rotis again at dinner.", "en", 8, 20),
      R("khana theek se banao please", "hinglish", 10, 20, 10),
      R("roti andar se kachchi hai", "hinglish", 12, 20)])
add("Roads & Lights", "Street light not working near main gate", "The approach road to the main gate is unlit at night.",
    "high", spot="main gate approach road", reports=[
      R("main gate ke paas light nahi jal rahi, raat me dar lagta hai", "hinglish", 2, 21),
      R("Street light near the main gate is dead.", "en", 4, 20),
      R("gate ke paas andhera rehta hai", "hinglish", 6, 21, 30),
      R("The road to the gate is pitch dark after 7pm.", "en", 8, 19, 45),
      R("light theek karwao gate pe", "hinglish", 11, 21),
      R("Still no light on the gate road.", "en", 12, 20, 30)])

# ---- in progress (3) ----
add("Electrical & AC", "Ceiling fan not working in room A114", "The ceiling fan has stopped completely.",
    "high", "in_progress", building="BH1 (Kanhar)", spot="A114", reports=[
      R("fan band ho gaya hai room me", "hinglish", 6, 15), R("Room fan dead since yesterday.", "en", 7, 11)])
add("Water Coolers", "Water cooler not cooling near library", "The cooler dispenses only room-temperature water.",
    "medium", "in_progress", spot="library entrance", reports=[
      R("library ke bahar cooler ka paani garam aa raha hai", "hinglish", 5, 13),
      R("Water cooler outside the library is not cooling.", "en", 8, 14)])
add("Classrooms & Labs", "Projector not working in lecture hall", "The projector in the hall does not display.",
    "high", "in_progress", building="Academic Building", spot="LH-2", reports=[
      R("projector kaam nahi kar raha LH-2 me", "hinglish", 9, 10),
      R("Projector in LH-2 fails to turn on.", "en", 10, 11)])

# ---- resolved (4) ----
add("Furniture & Doors", "Broken door lock in room C208", "The room door lock was broken and would not latch.",
    "high", "resolved", building="GH1 (Indravati)", spot="C208",
    note="Lock replaced by hostel maintenance on 5 Oct.", reports=[
      R("room ka lock toot gaya hai", "hinglish", 1, 18), R("Door does not lock at all.", "en", 2, 9)])
add("Portals & Accounts", "Cannot log in to the academic portal", "Login failed with a server error.",
    "medium", "resolved", note="Portal account unlocked by IT Cell.", reports=[
      R("portal pe login nahi ho raha", "hinglish", 2, 12)])
add("Animals & Safety", "Stray dogs near the hostel entrance at night", "A pack of stray dogs gathers at the entrance.",
    "urgent", "resolved", spot="BH2 entrance", note="Municipal team relocated the dogs on 7 Oct.", reports=[
      R("hostel ke gate pe kutte bahut hai raat me", "hinglish", 3, 22),
      R("Stray dogs chased a student near the entrance.", "en", 4, 23)])
add("Service & Timings", "Mess closed before the scheduled time", "The mess shut 20 minutes early at dinner.",
    "low", "resolved", building="Mess", note="Mess timings reinstated after a committee notice.", reports=[
      R("mess time se pehle band kar dete hai", "hinglish", 5, 21)])

# ---- the four Others ----
add("Other", "Laundry service not collecting clothes", "Laundry pickup has been skipped for over a week.",
    "medium", suggested="Laundry", building="BH1 (Kanhar)", reports=[
      R("laundry wale kapde lene nahi aa rahe", "hinglish", 6, 10),
      R("No laundry pickup for 8 days.", "en", 8, 12)])
add("Other", "Laundry returning clothes damaged", "Several garments came back torn.",
    "medium", suggested="Laundry", building="BH2 (Gopad)", reports=[
      R("laundry se kapde phat ke aaye", "hinglish", 7, 17)])
add("Other", "Laundry charges unclear this month", "Billing for laundry was higher than posted rates.",
    "low", suggested="Laundry", reports=[R("laundry ka bill zyada aaya hai", "hinglish", 10, 19)])
add("Other", "Gym equipment broken and unusable", "Two machines in the gym are out of order.",
    "medium", suggested="Gym", spot="gym hall", reports=[
      R("gym ki machine kharab hai", "hinglish", 8, 18),
      R("Treadmill and cable machine both broken.", "en", 11, 18, 30)])

# ---- the long tail: 1-3 reports each, spread over every domain ----
TAIL = [
  ("Electrical & AC", "Light switch sparking in room B201", "urgent", "GH1 (Indravati)", "B201", None),
  ("Electrical & AC", "AC not cooling in room F304", "high", "MSH (Married Hostel)", "F304", None),
  ("Electrical & AC", "Tube light flickering in corridor", "low", "BH1 (Kanhar)", "2F corridor", None),
  ("Plumbing & Water", "Tap leaking in 2nd-floor washroom", "medium", "GH1 (Indravati)", "2F washroom", None),
  ("Plumbing & Water", "Blocked drain in ground-floor washroom", "high", "BH1 (Kanhar)", "ground-floor washroom", None),
  ("Plumbing & Water", "Low water pressure in room D305", "medium", "MSH (Married Hostel)", "D305", None),
  ("Furniture & Doors", "Broken chair in room E112", "low", "BH1 (Kanhar)", "E112", None),
  ("Furniture & Doors", "Window latch broken in room A227", "medium", "GH1 (Indravati)", "A227", None),
  ("Furniture & Doors", "Study table wobbling in room B322", "low", "BH2 (Gopad)", "B322", None),
  ("Housekeeping", "Garbage not collected from corridor", "medium", "BH2 (Gopad)", "3F corridor", None),
  ("Housekeeping", "Dust and cobwebs in the common room", "low", "MSH (Married Hostel)", "common room", None),
  ("Food Quality", "Watery dal served at lunch", "medium", "Mess", None, "lunch"),
  ("Food Quality", "Stale bread at breakfast", "high", "Mess", None, "breakfast"),
  ("Hygiene", "Dirty plates stacked at the washing area", "medium", "Mess", None, "dinner"),
  ("Hygiene", "Unclean water jugs on mess tables", "medium", "Mess", None, "snacks"),
  ("Service & Timings", "Long queue at breakfast every day", "low", "Mess", None, None),
  ("Wi-Fi & LAN", "Slow Wi-Fi in the library reading hall", "medium", "Academic Building", "library reading hall", None),
  ("Wi-Fi & LAN", "LAN port dead in room C208", "medium", "GH1 (Indravati)", "C208", None),
  ("Portals & Accounts", "Grade card not loading on the portal", "medium", None, None, None),
  ("Classrooms & Labs", "Broken benches in the chemistry lab", "medium", "Academic Building", "chemistry lab", None),
  ("Classrooms & Labs", "AC not working in the computer lab", "high", "Academic Building", "computer lab", None),
  ("Water Coolers", "Water cooler leaking near the mess", "medium", None, "outside mess", None),
  ("Water Coolers", "No drinking water point in the academic lobby", "medium", None, "academic lobby", None),
  ("Roads & Lights", "Pothole on the road to the hostels", "high", None, "hostel approach road", None),
  ("Roads & Lights", "Broken paver blocks near the canteen", "low", None, "canteen walkway", None),
  ("Transport", "Campus bus skipped the evening trip", "high", None, "main gate bus stop", None),
  ("Transport", "Bus timings not displayed at the stop", "low", None, "main gate bus stop", None),
  ("Animals & Safety", "Monkeys entering hostel balconies", "high", "BH1 (Kanhar)", "4F balcony", None),
  ("Animals & Safety", "Snake spotted near the sports ground", "urgent", None, "sports ground", None),
]
HIN = ["theek karwa do please", "bahut problem ho rahi hai", "kuch karo bhai", "jaldi dekh lo",
       "kaafi dino se aisa hai", "please isko fix karo"]
for i, (cat, summ, sev, bld, spot, meal) in enumerate(TAIL):
    n = (i % 3) + 1 + (1 if i % 5 == 0 else 0)
    reports = []
    for k in range(n):
        day = (i * 3 + k * 2) % 13
        if (i + k) % 2:
            reports.append(R(f"{summ.lower()} - {random.choice(HIN)}", "hinglish", day, 10 + (k * 3) % 11))
        else:
            reports.append(R(summ + ".", "en", day, 11 + (k * 4) % 10))
    add(cat, summ, summ + ".", sev, building=bld, spot=spot, meal=meal, reports=reports)

out = {"complaints": C}
total = sum(len(c["reports"]) for c in C)
Path("seed/complaints.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
hin = sum(1 for c in C for r in c["reports"] if r["language"] in ("hinglish", "hi"))
dom = [c for c in C if len(c["reports"]) >= 6]
print(f"wrote seed/complaints.json: {len(C)} complaints, {total} reports, "
      f"{hin}/{total} ({100*hin//total}%) Hinglish, {len(dom)} dominant (6-14 reports)")
print("resolved:", sum(1 for c in C if c["status"]=="resolved"), "| in_progress:",
      sum(1 for c in C if c["status"]=="in_progress"), "| Other:", sum(1 for c in C if c["category"]=="Other"))
bad = [c for c in C if c["building"]=="BH2 (Gopad)" and c["category"] in ("Electrical & AC","Plumbing & Water")]
print("BH2 electrical/plumbing (must be 0... except the sparking one, check):", [c["summary"] for c in bad])
demo = [c for c in C if c["category"]=="Hygiene" and c["building"]=="Mess" and c["severity"]=="high"]
print("demo complaint reports (must be 4):", [len(c["reports"]) for c in demo])
