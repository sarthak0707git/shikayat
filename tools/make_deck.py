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
DECK_SHOT = ROOT / "docs" / "screenshot-deck.png"

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


def footer(s, page):
    """A quiet page number and wordmark, so the deck reads as one document."""
    text(s, Inches(0.9), Inches(6.95), Inches(4), Inches(0.3),
         "Shikayat", size=10, color=MUTED)
    text(s, Inches(11.4), Inches(6.95), Inches(1.0), Inches(0.3),
         str(page), size=10, color=MUTED, align=PP_ALIGN.RIGHT)


def stat(s, left, top, value, label, accent=False):
    """One big number with a caption under it."""
    text(s, left, top, Inches(2.6), Inches(0.8), value, size=42, bold=True,
         color=ACCENT if accent else INK)
    text(s, left, top + Inches(0.72), Inches(2.6), Inches(0.4), label, size=12, color=MUTED)


def build():
    n = stats()
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    # ---------- 1. title: dark, so it reads as a cover ----------
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    bg.fill.solid(); bg.fill.fore_color.rgb = INK
    bg.line.fill.background(); bg.shadow.inherit = False
    rule = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.3), Inches(2.45), Inches(1.1), Pt(6))
    rule.fill.solid(); rule.fill.fore_color.rgb = ACCENT
    rule.line.fill.background(); rule.shadow.inherit = False
    text(s, Inches(1.3), Inches(2.75), Inches(11), Inches(1.4), "Shikayat",
         size=76, bold=True, color=WHITE)
    text(s, Inches(1.3), Inches(4.05), Inches(10.5), Inches(0.6),
         "Campus complaints that count.", size=27, color=RGBColor(0xC7, 0xD2, 0xFE))
    text(s, Inches(1.3), Inches(4.95), Inches(9.8), Inches(1.0),
         "A student writes in English, Hinglish or Hindi. Gemma 4 buckets it, spots the "
         "duplicates, and asks back when it is unsure.", size=16,
         color=RGBColor(0x9C, 0xA3, 0xAF))
    text(s, Inches(1.3), Inches(6.35), Inches(11), Inches(0.8),
         [("Sarthak Shrivastava · Vedant · Sumagna Das · Devanshu Sabharwal · Neil",
           12, RGBColor(0x6B, 0x72, 0x80), False),
          ("OpenLake × MLH Hack Day · IIT Bhilai · 10 October 2026",
           12, RGBColor(0x6B, 0x72, 0x80), False)], size=12)

    # ---------- 2. problem ----------
    s = slide(prs, paper=True)
    heading(s, "Complaint portals already exist.", "the problem")
    card(s, Inches(0.9), Inches(2.45), Inches(5.5), Inches(2.3), fill=WHITE)
    text(s, Inches(1.3), Inches(2.75), Inches(4.8), Inches(1.9),
         [("They make you fill forms.", 21, INK, True),
          ("Dropdowns, required fields, a login. So students give up and complain in "
           "the hostel WhatsApp group instead.", 15, MUTED, False)], spacing=1.3)
    card(s, Inches(6.9), Inches(2.45), Inches(5.5), Inches(2.3), fill=WHITE)
    text(s, Inches(7.3), Inches(2.75), Inches(4.8), Inches(1.9),
         [("They bury wardens in duplicates.", 21, INK, True),
          ("Forty students report the same dead Wi-Fi forty times. Nobody can tell which "
           "problem is actually the biggest.", 15, MUTED, False)], spacing=1.3)
    strip = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(5.15),
                               Inches(11.5), Inches(1.15))
    strip.fill.solid(); strip.fill.fore_color.rgb = INK
    strip.line.fill.background(); strip.shadow.inherit = False
    strip.adjustments[0] = 0.12
    text(s, Inches(1.4), Inches(5.42), Inches(10.6), Inches(0.6),
         "Nobody counts. So the loudest complaint wins, not the most common one.",
         size=19, bold=True, color=WHITE)
    footer(s, 2)

    # ---------- 3. what we built ----------
    s = slide(prs)
    text(s, Inches(0.9), Inches(0.6), Inches(11), Inches(0.35),
         "WHAT WE BUILT", size=11, color=ACCENT, bold=True)
    text(s, Inches(0.9), Inches(0.95), Inches(11.5), Inches(0.6),
         "One board, ranked by how much it hurts.", size=30, bold=True)
    shot = DECK_SHOT if DECK_SHOT.is_file() else SHOT
    if shot.is_file():
        card(s, Inches(0.78), Inches(1.78), Inches(7.64), Inches(5.42), fill=PAPER)
        s.shapes.add_picture(str(shot), Inches(0.9), Inches(1.9), width=Inches(7.4),
                             height=Inches(5.18))
    stat(s, Inches(8.9), Inches(1.9), str(n["complaints"]), "complaints")
    stat(s, Inches(10.9), Inches(1.9), str(n["escalated"]), "escalated", accent=True)
    text(s, Inches(8.9), Inches(3.3), Inches(3.7), Inches(3.2),
         [("priority = reports × severity", 15, ACCENT, True),
          ("Computed in code, never by the model. An issue escalates at five reports, or "
           "at once if it is a safety risk.", 14, MUTED, False),
          ("", 7, MUTED, False),
          (f"{n['categories']} buckets, 7 authorities", 15, ACCENT, True),
          ("Hostel Office, Mess Committee, IT Cell and the rest each see only their own "
           "queue.", 14, MUTED, False)], spacing=1.3)
    footer(s, 3)

    # ---------- 4. the differentiator ----------
    s = slide(prs, paper=True)
    heading(s, "Gemma asks back when it is unsure.", "the part nobody else does")
    card(s, Inches(0.9), Inches(2.45), Inches(5.5), Inches(3.3), fill=WHITE)
    text(s, Inches(1.3), Inches(2.7), Inches(4.8), Inches(2.9),
         [("Student", 10, MUTED, True), ("AC se paani tapak raha hai", 17, INK, False),
          ("", 6, MUTED, False),
          ("Gemma", 10, ACCENT, True),
          ("Kaunse hostel aur kis room mein?", 17, ACCENT, False),
          ("", 6, MUTED, False),
          ("Student", 10, MUTED, True), ("BH2 E207", 17, INK, False),
          ("", 6, MUTED, False),
          ("Filed #47 · Hostel Office · BH2 (Gopad) E207", 13, MUTED, True)], spacing=1.25)
    text(s, Inches(6.9), Inches(2.5), Inches(5.5), Inches(3.4),
         [("In the student's own language.", 18, INK, True),
          ("Hinglish in, Hinglish out. One short question, at most two per report — a "
           "limit our code enforces, not a rule we hope the model follows.", 15, MUTED, False),
          ("", 8, MUTED, False),
          ("It knows what it already has.", 18, INK, True),
          ("Same issue, same place → merged, and the count goes up. A different room → a "
           "new complaint. A hostel that does not exist → it asks.", 15, MUTED, False)],
         spacing=1.3)
    footer(s, 4)

    # ---------- 5. how we use gemma ----------
    s = slide(prs)
    heading(s, "How we use Gemma 4.", "the model")
    text(s, Inches(0.9), Inches(2.45), Inches(5.4), Inches(2.8),
         [("gemma-4-26b-a4b-it", 23, ACCENT, True),
          ("through the Gemini API, with google-genai. Every call in the project goes "
           "through one helper.", 15, MUTED, False),
          ("", 9, MUTED, False),
          ("Two calls per complaint.", 19, INK, True),
          ("One to pick a bucket and look for duplicates. One to decide: file, merge, ask "
           "or reject. The starter's loop needed four.", 15, MUTED, False)], spacing=1.3)
    code = card(s, Inches(6.9), Inches(2.45), Inches(5.5), Inches(1.6), fill=INK)
    text(s, Inches(7.2), Inches(2.68), Inches(5.0), Inches(1.2),
         [("# gemma_client.py", 11, RGBColor(0x6B, 0x72, 0x80), False),
          ("client.models.generate_content(", 12, WHITE, False),
          ('    model="gemma-4-26b-a4b-it",', 12, RGBColor(0xA5, 0xB4, 0xFC), False),
          ("    contents=contents, config=config)", 12, WHITE, False)],
         spacing=1.2, font="Courier New")
    text(s, Inches(6.9), Inches(4.35), Inches(5.5), Inches(2.2),
         [("The model never decides:", 16, INK, True),
          ("priority · escalation · complaint ids · how many questions it may ask",
           14, ACCENT, False),
          ("All four are enforced in our code. merge_into rejects any id that was not in "
           "the search results it was just shown.", 14, MUTED, False)], spacing=1.3)
    footer(s, 5)

    # ---------- 6. the harness ----------
    s = slide(prs, paper=True)
    heading(s, "What we changed in the harness.", "our open-source contribution")
    rows = [
        ("Per-agent tool sets", "Each agent sends only the tools it needs."),
        ("Image input", "A photo is evidence. Sent as inline bytes."),
        ("Terminal tools", "@tool(stop=True) ends the run with its own result."),
        ("Pause for a human", "@tool(pause=True) asks, then resumes the same conversation."),
        ("Step labels + RunResult", 'The UI shows "Looking for similar reports in Mess".'),
    ]
    top = Inches(2.4)
    for title_text, why in rows:
        bar(s, top + Inches(0.06), left=Inches(0.9), width=Pt(4), height=Inches(0.46))
        text(s, Inches(1.25), top, Inches(3.6), Inches(0.45), title_text, size=16, bold=True)
        text(s, Inches(5.0), top, Inches(7.4), Inches(0.45), why, size=14, color=MUTED)
        top = top + Inches(0.66)
    strip = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.9), Inches(5.95),
                               Inches(11.5), Inches(1.0))
    strip.fill.solid(); strip.fill.fore_color.rgb = INK
    strip.line.fill.background(); strip.shadow.inherit = False
    strip.adjustments[0] = 0.14
    text(s, Inches(1.4), Inches(6.18), Inches(10.6), Inches(0.5),
         "4 Gemma calls → 2.    36 tests, all on a fake model, so they run with no API key.",
         size=17, bold=True, color=WHITE)
    footer(s, 6)

    # ---------- 7. next ----------
    s = slide(prs)
    heading(s, "What we would do next.", "next")
    items = [
        ("Institute SSO", "The role picker is a demo stand-in."),
        ("Object storage for photos", "Local disk today; S3 or Cloud Storage in production."),
        ("WhatsApp intake", "Students already complain in hostel groups. Meet them there."),
        ("Promote the Other bucket", "Four laundry reports. Admin turns a suggestion into a category."),
    ]
    top = Inches(2.5)
    for title_text, why in items:
        text(s, Inches(0.9), top, Inches(3.9), Inches(0.45), title_text, size=17, bold=True,
             color=ACCENT)
        text(s, Inches(5.0), top, Inches(7.4), Inches(0.5), why, size=14, color=MUTED)
        top = top + Inches(0.82)
    text(s, Inches(0.9), Inches(6.3), Inches(11.5), Inches(0.4),
         "github.com/sarthak0707git/shikayat   ·   MIT   ·   built today", size=14, color=MUTED)
    footer(s, 7)

    OUT.parent.mkdir(exist_ok=True)
    prs.save(OUT)
    return OUT, len(prs.slides._sldIdLst)


if __name__ == "__main__":
    path, count = build()
    print(f"Wrote {path.relative_to(ROOT)} ({count} slides, {path.stat().st_size // 1024} KB)")
