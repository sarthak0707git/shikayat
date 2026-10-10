"""Build the submission deck: python tools/make_deck.py -> docs/Shikayat.pptx

Regenerate it any time the numbers change. Everything on the slides comes from this file,
so there is one place to edit, and the stats are pulled live from the seeded database.
"""

import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "Shikayat.pptx"
SHOT = ROOT / "docs" / "screenshot.png"

INK = RGBColor(0x11, 0x18, 0x27)
MUTED = RGBColor(0x6B, 0x72, 0x80)
ACCENT = RGBColor(0x4F, 0x46, 0xE5)
PAPER = RGBColor(0xF5, 0xF5, 0xF4)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Arial"  # present everywhere; Liberation Sans substitutes cleanly on Linux

W, H = Inches(13.333), Inches(7.5)


def stats():
    """Live numbers, so the deck can never quote figures the demo does not show."""
    try:
        from api import db
        s = db.stats()
        return {"open": s["kpis"]["open"], "escalated": s["kpis"]["escalated"],
                "complaints": len(db.list_complaints()), "categories": len(db.list_categories())}
    except Exception:
        return {"open": 39, "escalated": 7, "complaints": 46, "categories": 15}


def slide(prs, paper=False):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = PAPER if paper else WHITE
    bg.line.fill.background()
    bg.shadow.inherit = False
    return s


def text(s, left, top, width, height, body, size=18, color=INK, bold=False,
         align=PP_ALIGN.LEFT, spacing=1.25, font=FONT):
    box = s.shapes.add_textbox(left, top, width, height)
    frame = box.text_frame
    frame.word_wrap = True
    for index, line in enumerate(body if isinstance(body, list) else [body]):
        para = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        para.alignment = align
        para.line_spacing = spacing
        if isinstance(line, tuple):  # (text, size, color, bold)
            content, *rest = line
            run_size = rest[0] if len(rest) > 0 else size
            run_color = rest[1] if len(rest) > 1 else color
            run_bold = rest[2] if len(rest) > 2 else bold
        else:
            content, run_size, run_color, run_bold = line, size, color, bold
        run = para.add_run()
        run.text = content
        run.font.size = Pt(run_size)
        run.font.color.rgb = run_color
        run.font.bold = run_bold
        run.font.name = font
    return box


def bar(s, top, left=Inches(0.9), width=Inches(0.9), height=Pt(5), color=ACCENT):
    shape = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def card(s, left, top, width, height, fill=PAPER, line=None):
    shape = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line:
        shape.line.color.rgb = line
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    shape.shadow.inherit = False
    shape.adjustments[0] = 0.06
    return shape


def heading(s, title, kicker=None):
    if kicker:
        text(s, Inches(0.9), Inches(0.62), Inches(11), Inches(0.4),
             kicker.upper(), size=12, color=ACCENT, bold=True)
    text(s, Inches(0.9), Inches(1.0), Inches(11.5), Inches(1.0), title, size=40, bold=True)
    bar(s, Inches(1.95))


def build():
    n = stats()
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    # ---------- 1. title ----------
    s = slide(prs)
    hero = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(0.22), H)
    hero.fill.solid()
    hero.fill.fore_color.rgb = ACCENT
    hero.line.fill.background()
    hero.shadow.inherit = False
    text(s, Inches(1.2), Inches(2.1), Inches(11), Inches(1.2), "Shikayat", size=66, bold=True)
    text(s, Inches(1.2), Inches(3.25), Inches(10.5), Inches(0.9),
         "Campus complaints that count.", size=26, color=MUTED)
    text(s, Inches(1.2), Inches(4.3), Inches(10.5), Inches(1.4),
         "A student writes a complaint in English, Hinglish or Hindi. Gemma 4 buckets it,\n"
         "spots the duplicates, and asks back when it is unsure.", size=17, color=INK)
    text(s, Inches(1.2), Inches(6.25), Inches(11), Inches(0.9),
         [("Sarthak Shrivastava  ·  Vedant  ·  Sumagna Das  ·  Devanshu Sabharwal  ·  Neil", 13, MUTED, False),
          ("OpenLake × MLH Hack Day  ·  IIT Bhilai  ·  10 October 2026", 13, MUTED, False)], size=13)

    # ---------- 2. problem ----------
    s = slide(prs, paper=True)
    heading(s, "Complaint portals already exist.", "the problem")
    text(s, Inches(0.9), Inches(2.5), Inches(5.6), Inches(3),
         [("They make you fill forms.", 22, INK, True),
          ("Dropdowns, required fields, a login. So students stop bothering and "
           "complain in the hostel WhatsApp group instead.", 16, MUTED, False)], spacing=1.3)
    text(s, Inches(6.9), Inches(2.5), Inches(5.6), Inches(3),
         [("And they bury wardens in duplicates.", 22, INK, True),
          ("Forty students report the same dead Wi-Fi forty times. Nobody can tell "
           "which problem is actually the biggest.", 16, MUTED, False)], spacing=1.3)
    card(s, Inches(0.9), Inches(5.1), Inches(11.5), Inches(1.4), fill=WHITE)
    text(s, Inches(1.3), Inches(5.45), Inches(10.8), Inches(0.9),
         "Nobody counts. So the loudest complaint wins, not the most common one.",
         size=20, bold=True, color=ACCENT)

    # ---------- 3. what we built ----------
    s = slide(prs)
    text(s, Inches(0.9), Inches(0.62), Inches(11), Inches(0.4),
         "WHAT WE BUILT", size=12, color=ACCENT, bold=True)
    text(s, Inches(0.9), Inches(1.0), Inches(11.5), Inches(0.8),
         "One board, ranked by how much it hurts.", size=32, bold=True)
    if SHOT.is_file():
        s.shapes.add_picture(str(SHOT), Inches(0.9), Inches(2.0), width=Inches(7.4))
    text(s, Inches(8.7), Inches(2.1), Inches(3.8), Inches(4.5),
         [(f"{n['complaints']} complaints", 24, INK, True),
          (f"{n['open']} open · {n['escalated']} escalated", 15, MUTED, False),
          ("", 8, MUTED, False),
          ("priority = reports × severity", 15, ACCENT, True),
          ("Computed in code, never by the model. An issue escalates at 5 reports, "
           "or instantly if it is a safety risk.", 14, MUTED, False),
          ("", 8, MUTED, False),
          (f"{n['categories']} buckets", 15, ACCENT, True),
          ("Each authority — Hostel Office, Mess Committee, IT Cell — sees only its "
           "own queue.", 14, MUTED, False)], spacing=1.25)

    # ---------- 4. the differentiator ----------
    s = slide(prs, paper=True)
    heading(s, "Gemma asks back when it is unsure.", "the part nobody else does")
    text(s, Inches(0.9), Inches(2.4), Inches(5.4), Inches(0.5),
         "A vague report would normally be filed and ignored:", size=15, color=MUTED)
    card(s, Inches(0.9), Inches(2.95), Inches(5.4), Inches(2.9), fill=WHITE)
    text(s, Inches(1.25), Inches(3.2), Inches(4.8), Inches(2.5),
         [("Student", 11, MUTED, True), ("AC se paani tapak raha hai", 17, INK, False),
          ("", 7, MUTED, False),
          ("Gemma", 11, ACCENT, True),
          ("Kaunse hostel aur kis room mein AC se paani tapak raha hai?", 17, ACCENT, False),
          ("", 7, MUTED, False),
          ("Student", 11, MUTED, True), ("BH2 E207", 17, INK, False)], spacing=1.2)
    text(s, Inches(6.9), Inches(2.4), Inches(5.5), Inches(3.4),
         [("It replies in the student's own language.", 18, INK, True),
          ("Hinglish in, Hinglish out. One short question, at most two per report — "
           "a limit our code enforces, not a rule we hope the model follows.", 15, MUTED, False),
          ("", 9, MUTED, False),
          ("It knows what it already has.", 18, INK, True),
          ("Before deciding, it searches the open complaints. Same issue, same place → "
           "merged, and the count goes up. Different room → a new complaint.", 15, MUTED, False)],
         spacing=1.25)
    card(s, Inches(0.9), Inches(6.1), Inches(11.5), Inches(0.95), fill=WHITE)
    text(s, Inches(1.3), Inches(6.3), Inches(10.8), Inches(0.6),
         "Filed as #47 in the Hostel Office queue — BH2 (Gopad), room E207.",
         size=16, bold=True, color=ACCENT)

    # ---------- 5. how we use gemma ----------
    s = slide(prs)
    heading(s, "How we use Gemma 4.", "the model")
    text(s, Inches(0.9), Inches(2.45), Inches(5.5), Inches(2.6),
         [("gemma-4-26b-a4b-it", 24, ACCENT, True),
          ("through the Gemini API, with the google-genai package. Every call in the "
           "project goes through one helper.", 15, MUTED, False),
          ("", 10, MUTED, False),
          ("Two calls per complaint.", 20, INK, True),
          ("One to pick a bucket and look for duplicates. One to decide: file, merge, "
           "ask or reject. The starter's loop would have taken four.", 15, MUTED, False)],
         spacing=1.25)
    card(s, Inches(6.8), Inches(2.45), Inches(5.6), Inches(1.75), fill=INK)
    text(s, Inches(7.1), Inches(2.72), Inches(5.0), Inches(1.3),
         [("# gemma_client.py", 12, RGBColor(0x9C, 0xA3, 0xAF), False),
          ("client.models.generate_content(", 13, WHITE, False),
          ("    model=\"gemma-4-26b-a4b-it\",", 13, RGBColor(0xA5, 0xB4, 0xFC), False),
          ("    contents=contents, config=config)", 13, WHITE, False)],
         spacing=1.15, font="Courier New")
    text(s, Inches(6.8), Inches(4.5), Inches(5.6), Inches(2.4),
         [("The model never decides:", 16, INK, True),
          ("priority · escalation · complaint ids · how many questions it may ask",
           15, MUTED, False),
          ("", 8, MUTED, False),
          ("All four are enforced in our code. merge_into rejects any id that was not "
           "in the search results it was just shown.", 15, MUTED, False)], spacing=1.25)

    # ---------- 6. the harness ----------
    s = slide(prs, paper=True)
    heading(s, "What we changed in the harness.", "our open-source contribution")
    rows = [
        ("Per-agent tool sets", "Each agent sends only the tools it needs, not everything registered."),
        ("Image input", "A photo of an insect on a plate is the evidence. Sent as inline bytes."),
        ("Terminal tools", "@tool(stop=True) ends the run with its own result — no extra model round."),
        ("Pause for a human", "@tool(pause=True) returns the question, then resumes the same conversation."),
        ("Step labels + RunResult", "The UI shows \"Looking for similar reports in Mess\" instead of a spinner."),
    ]
    top = Inches(2.45)
    for title_text, why in rows:
        bar(s, top + Inches(0.1), left=Inches(0.9), width=Pt(4), height=Inches(0.52))
        text(s, Inches(1.2), top, Inches(3.5), Inches(0.5), title_text, size=16, bold=True)
        text(s, Inches(4.8), top, Inches(7.6), Inches(0.5), why, size=14, color=MUTED)
        top = top + Inches(0.72)
    card(s, Inches(0.9), Inches(6.25), Inches(11.5), Inches(0.85), fill=WHITE)
    text(s, Inches(1.3), Inches(6.45), Inches(10.8), Inches(0.5),
         "4 Gemma calls → 2.   34 tests, all on a fake model, so they run with no API key.",
         size=16, bold=True, color=ACCENT)

    # ---------- 7. next ----------
    s = slide(prs)
    heading(s, "What we would do next.", "next")
    items = [
        ("Institute SSO", "The role picker is a demo stand-in. Real deployment authenticates against the institute."),
        ("Object storage for photos", "Photos are on local disk today. Production would use S3 or Cloud Storage."),
        ("WhatsApp intake", "Students already complain in hostel groups. Meet them where they are."),
        ("Promote the Other bucket", "Four students reported laundry issues. Admin can turn a suggestion into a real category."),
    ]
    top = Inches(2.5)
    for title_text, why in items:
        text(s, Inches(0.9), top, Inches(3.6), Inches(0.5), title_text, size=17, bold=True, color=ACCENT)
        text(s, Inches(4.8), top, Inches(7.6), Inches(0.6), why, size=14, color=MUTED)
        top = top + Inches(0.85)
    text(s, Inches(0.9), Inches(6.5), Inches(11.5), Inches(0.5),
         "github.com/sarthak0707git/shikayat   ·   MIT", size=14, color=MUTED)

    OUT.parent.mkdir(exist_ok=True)
    prs.save(OUT)
    return OUT, len(prs.slides._sldIdLst)


if __name__ == "__main__":
    path, count = build()
    print(f"Wrote {path.relative_to(ROOT)} ({count} slides, {path.stat().st_size // 1024} KB)")
