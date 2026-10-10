"""Checks this project before we submit it. Run it from the repo root:

    python tools/check_shikayat.py

Each check prints PASS, FAIL or WARN with a one-line fix. Exit code is 1 if anything FAILED.
Standard library only, so it runs on any laptop with Python.

This is the Shikayat-specific gate. The organisers' own script, tools/check_submission.py,
must also show no FAIL - run both.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".cache", "wheelhouse",
             ".pytest_cache", "dist", "build", ".mypy_cache", ".ruff_cache"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SLIDE_EXTENSIONS = {".pptx", ".ppt", ".pdf", ".key", ".odp"}
MODEL = "gemma-4-26b-a4b-it"
KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z_-]{35}")
SKILL_DIR = Path("skills/campus-complaint-triage")


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def project_files(root):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_file() and not SKIP_DIRS.intersection(relative.parts):
            yield path


def git(root, *args):
    """Run a git command. Returns its output, or None if git or the repo is not there."""
    try:
        done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout if done.returncode == 0 else None


# ---------- 1. the shared rules ----------

def check_docs(root):
    missing = [name for name in ("docs/BRIEF.md", "CLAUDE.md", "AGENTS.md")
               if not (root / name).is_file()]
    if missing:
        return "FAIL", f"missing: {', '.join(missing)}", "These are the shared rules. Restore them from git history."
    return "PASS", "docs/BRIEF.md, CLAUDE.md and AGENTS.md are all present", ""


# ---------- 2. license ----------

def check_license(root):
    path = root / "LICENSE"
    if not path.is_file():
        return "FAIL", "no LICENSE file", "Keep the MIT LICENSE that came with the starter."
    text = " ".join(read_text(path).lower().split())
    if "permission is hereby granted, free of charge" not in text:
        return "FAIL", "LICENSE is not the MIT license", "Restore the MIT LICENSE from the starter."
    if "[organizer name]" in text:
        return "FAIL", "LICENSE still says [ORGANIZER NAME]", "Replace it with the five team members' names."
    return "PASS", "MIT license, with a real name in it", ""


# ---------- 3. readme ----------

def check_readme(root):
    readme = read_text(root / "README.md")
    if not readme:
        return "FAIL", "no README.md", "Write a README. The judges read it."
    problems = []
    if MODEL not in readme:
        problems.append(f"does not name the model ({MODEL})")
    if not re.search(r"^#+\s*how to run", readme, re.IGNORECASE | re.MULTILINE):
        problems.append('no "## How to run" heading')
    if not re.search(r"^#+\s*what we changed in the harness", readme, re.IGNORECASE | re.MULTILINE):
        problems.append('no "## What we changed in the harness" heading')
    if "generate_content" not in readme:
        problems.append("does not show the line of code that calls the model")

    images = (re.findall(r"!\[[^\]]*\]\(([^)\s]+)", readme)
              + re.findall(r'<img[^>]+src="([^"]+)"', readme))
    local = [i for i in images if not i.startswith(("http://", "https://"))]
    if not images:
        problems.append("no screenshot (add ![screenshot](docs/screenshot.png))")
    else:
        broken = [i for i in local if not (root / i).is_file()]
        if broken:
            problems.append(f"screenshot file not found: {broken[0]}")

    if problems:
        return "FAIL", "README: " + "; ".join(problems), "Fix the README, then run this again."
    return "PASS", "README names the model, shows the call, has How to run, the harness write-up and a screenshot", ""


def check_team_named(root):
    readme = read_text(root / "README.md")
    match = re.search(r"^#+\s*team\s*$(.*?)(?=^#|\Z)", readme, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if not match:
        return "WARN", "README has no Team section", "Add a ## Team section with all five names."
    body = match.group(1)
    if "(P5" in body or "fills this in" in body or not body.strip():
        return "WARN", "README Team section is still a placeholder", "Put the five real names in."
    return "PASS", "README names the team", ""


# ---------- 4. the agent skill (MLH requirement) ----------

def _frontmatter(text):
    """The YAML-ish frontmatter as a dict. No PyYAML; we only need flat key: value pairs."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fields, key = {}, None
    for line in text[3:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^\s+", line) and key:  # a continuation of the previous value
            fields[key] += " " + line.strip()
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            fields[key] = value.strip().strip("\"'")
    return fields


def check_skill(root):
    skill = root / SKILL_DIR / "SKILL.md"
    if not skill.is_file():
        return "FAIL", f"no {SKILL_DIR}/SKILL.md", "MLH requires an Agent Skill file. See agentskills.io/specification."
    text = read_text(skill)
    fields = _frontmatter(text)
    problems = []

    name = fields.get("name", "")
    if not name:
        problems.append("frontmatter has no name")
    elif name != SKILL_DIR.name:
        problems.append(f'name "{name}" does not match the folder name "{SKILL_DIR.name}"')
    elif not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        problems.append(f'name "{name}" must be lowercase letters, digits and single hyphens')

    description = fields.get("description", "")
    if not description:
        problems.append("frontmatter has no description")
    elif len(description) > 1024:
        problems.append(f"description is {len(description)} characters, the limit is 1024")

    lines = len(text.splitlines())
    if lines >= 500:
        problems.append(f"SKILL.md is {lines} lines, the spec says keep it under 500")

    if problems:
        return "FAIL", "SKILL.md: " + "; ".join(problems), "Fix the skill, then run this again."
    return "PASS", f"SKILL.md valid (name {name}, {lines} lines, description {len(description)} chars)", ""


def check_skill_agrees_with_code(root):
    """The skill must teach the same buckets the code actually uses."""
    skill = root / SKILL_DIR / "SKILL.md"
    if not skill.is_file():
        return "WARN", "no SKILL.md to cross-check", "Write the skill first."
    text = read_text(skill) + "".join(
        read_text(p) for p in (root / SKILL_DIR).rglob("*.md") if p.is_file())
    try:
        sys.path.insert(0, str(root))
        from complaints.categories import BUILDINGS, CATEGORIES
    except Exception as error:
        return "WARN", f"could not import complaints.categories ({error})", "Run from the repo root."

    missing = [name for name in CATEGORIES if name not in text]
    if missing:
        return "FAIL", f"SKILL.md never mentions {len(missing)} of our categories: {', '.join(missing[:4])}", \
               "The skill and complaints/categories.py must list the same buckets."
    if not any(building in text for building in BUILDINGS):
        return "WARN", "SKILL.md mentions none of our real building names", \
               "Use BH1 (Kanhar), BH2 (Gopad), GH1 (Indravati), MSH (Married Hostel), Mess, Academic Building."
    return "PASS", f"SKILL.md covers all {len(CATEGORIES)} categories and uses our real buildings", ""


# ---------- 5. seed data ----------

def check_seed(root):
    problems = []
    complaints_file = root / "seed" / "complaints.json"
    cases_file = root / "seed" / "test_cases.json"

    if not complaints_file.is_file():
        problems.append("seed/complaints.json is missing")
    else:
        try:
            data = json.loads(read_text(complaints_file))
            items = data["complaints"] if isinstance(data, dict) else data
            reports = sum(len(c.get("reports") or []) for c in items)
            if len(items) < 30:
                problems.append(f"only {len(items)} complaints, the board will look empty")
            if reports < 80:
                problems.append(f"only {reports} reports")
        except (ValueError, KeyError, TypeError) as error:
            problems.append(f"seed/complaints.json is not valid ({error})")

    if not cases_file.is_file():
        problems.append("seed/test_cases.json is missing")
    else:
        try:
            data = json.loads(read_text(cases_file))
            cases = data["cases"] if isinstance(data, dict) else data
            if len(cases) < 12:
                problems.append(f"only {len(cases)} test cases, the brief asks for 12")
        except (ValueError, KeyError, TypeError) as error:
            problems.append(f"seed/test_cases.json is not valid ({error})")

    if problems:
        return "FAIL", "seed: " + "; ".join(problems), "Fix seed/, then run python -m api.seed --reset."
    return "PASS", "seed/complaints.json and seed/test_cases.json both load", ""


def check_demo_invariants(root):
    """Three things in the seed data the 90-second demo depends on."""
    path = root / "seed" / "complaints.json"
    if not path.is_file():
        return "WARN", "no seed/complaints.json to check", "Write the seed data first."
    try:
        data = json.loads(read_text(path))
        items = data["complaints"] if isinstance(data, dict) else data
    except (ValueError, KeyError, TypeError):
        return "WARN", "seed/complaints.json does not parse", "Fix the JSON first."

    weight = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
    problems = []

    demo = [c for c in items if c.get("category") == "Hygiene" and c.get("building") == "Mess"
            and c.get("severity") == "high" and c.get("status", "open") == "open"]
    if len(demo) != 1:
        problems.append(f"expected exactly 1 open high Hygiene/Mess complaint, found {len(demo)}")
    elif len(demo[0].get("reports") or []) != 4:
        problems.append(f"the demo mess-hygiene complaint has {len(demo[0].get('reports') or [])} "
                        "reports, it must have exactly 4 so the live report is the 5th")

    bad = [c["summary"] for c in items if c.get("building") == "BH2 (Gopad)"
           and c.get("category") in ("Electrical & AC", "Plumbing & Water")]
    if bad:
        problems.append(f"BH2 (Gopad) already has an electrical/plumbing complaint ({bad[0]!r}), "
                        "so demo step 3 would merge instead of filing new")

    ceiling = []
    for c in items:
        if c.get("status", "open") == "resolved":
            continue
        priority = len(c.get("reports") or []) * weight.get(c.get("severity"), 1)
        if priority > 18:
            ceiling.append(f"{c.get('summary')!r} at priority {priority}")
    if ceiling:
        problems.append(f"{len(ceiling)} open complaint(s) above priority 18 ({ceiling[0]}), so the "
                        "demo complaint will not reach #1 when it escalates to 20")

    if problems:
        return "FAIL", "demo data: " + "; ".join(problems), \
               "These three invariants are what make the 90-second demo work. See issue #6."
    return "PASS", "demo invariants hold (4-report mess complaint, clean BH2, priority ceiling 18)", ""


# ---------- 6. demo material ----------

def check_demo_photos(root):
    folder = root / "demo" / "photos"
    photos = [p for p in folder.glob("*") if p.suffix.lower() in IMAGE_EXTENSIONS] if folder.is_dir() else []
    if len(photos) < 3:
        return "FAIL", f"only {len(photos)} photo(s) in demo/photos/", \
               "Take 3-4 real campus photos (a leaking tap, a dirty washroom, a broken chair, food on a plate)."
    big = [p.name for p in photos if p.stat().st_size > 5 * 1024 * 1024]
    if big:
        return "WARN", f"{len(photos)} photos, but {big[0]} is over 5 MB", "The API rejects photos above 5 MB."
    return "PASS", f"{len(photos)} demo photos ready", ""


def check_slides(root):
    slides = [p for p in project_files(root) if p.suffix.lower() in SLIDE_EXTENSIONS
              and "brief" not in p.name.lower()]
    if not slides:
        return "FAIL", "no presentation in the repo", \
               "Commit the PPT (docs/Shikayat.pptx or .pdf) and put the share link in the README."
    return "PASS", f"presentation found: {slides[0].relative_to(root)}", ""


# ---------- 7. key safety ----------

def check_no_key(root):
    problems = []
    for path in project_files(root):
        if path.name == ".env" or path.stat().st_size > 2_000_000:
            continue
        for number, line in enumerate(read_text(path).splitlines(), 1):
            if KEY_PATTERN.search(line):
                problems.append(f"{path.relative_to(root)}:{number}")
    if problems:
        return "FAIL", "an API key is in: " + ", ".join(problems), \
               "Delete that key in Google AI Studio, make a new one, and remove it from the file."
    tracked = git(root, "ls-files")
    if tracked is not None and ".env" in tracked.splitlines():
        return "FAIL", ".env is tracked by git", \
               "Run: git rm --cached .env, commit, then delete the key in AI Studio and make a new one."
    return "PASS", "no API key in any tracked file, and .env is not tracked", ""


def check_gitignore(root):
    lines = [line.strip() for line in read_text(root / ".gitignore").splitlines()]
    missing = [want for want in (".env",) if want not in lines]
    if missing:
        return "FAIL", ".gitignore does not list .env", "Add a line with .env to .gitignore."
    return "PASS", ".gitignore lists .env", ""


# ---------- 8. the code still works ----------

def check_tests(root):
    python = root / ".venv" / "bin" / "python"
    if not python.is_file():
        return "WARN", "no .venv found, skipping the harness tests", "python -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt"
    try:
        done = subprocess.run([str(python), "-m", "pytest", "harness", "-q"],
                              cwd=root, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as error:
        return "WARN", f"could not run the harness tests ({error})", "Run: ./.venv/bin/python -m pytest harness"
    if done.returncode != 0:
        tail = (done.stdout or done.stderr).strip().splitlines()
        return "FAIL", "harness tests fail: " + (tail[-1] if tail else "see output"), \
               "Run ./.venv/bin/python -m pytest harness and fix it."
    summary = [l for l in (done.stdout or "").splitlines() if "passed" in l]
    return "PASS", f"harness tests pass ({summary[-1].strip() if summary else 'ok'})", ""


# ---------- 9. git ----------

def check_git(root):
    remotes = git(root, "remote", "-v") or ""
    dirty = git(root, "status", "--porcelain")
    problems = []
    if "github.com" not in remotes:
        problems.append("no GitHub remote")
    if dirty:
        problems.append(f"{len(dirty.splitlines())} uncommitted change(s)")
    if problems:
        return "WARN", "git: " + "; ".join(problems), "Commit and push. The repo must be public."
    return "WARN", "pushed to GitHub, nothing uncommitted. This script cannot check the repo is public", \
           "Open the repo in a private browser window to confirm it is public."


CHECKS = [
    ("Shared rules", check_docs),
    ("License", check_license),
    ("README", check_readme),
    ("Team", check_team_named),
    ("Agent skill", check_skill),
    ("Skill vs code", check_skill_agrees_with_code),
    ("Seed data", check_seed),
    ("Demo invariants", check_demo_invariants),
    ("Demo photos", check_demo_photos),
    ("Presentation", check_slides),
    ("Key safety", check_no_key),
    (".gitignore", check_gitignore),
    ("Harness tests", check_tests),
    ("GitHub", check_git),
]


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    results = []
    for name, check in CHECKS:
        try:
            status, message, fix = check(root)
        except Exception as error:  # a broken check must not hide the other checks
            status, message, fix = "WARN", f"the {name} check itself crashed: {error}", ""
        results.append((name, status, message, fix))
        print(f"{status:<4}  {name}: {message}")
        if fix and status != "PASS":
            print(f"      Fix: {fix}")

    failed = [name for name, status, *_ in results if status == "FAIL"]
    warned = [name for name, status, *_ in results if status == "WARN"]
    print()
    if failed:
        print("FAILED: " + ", ".join(failed))
    else:
        print("No FAILs." + (f" Check the {len(warned)} WARN line(s), then submit." if warned else " Ready to submit."))
    print("Also run: python tools/check_submission.py   (the organisers' own gate)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
