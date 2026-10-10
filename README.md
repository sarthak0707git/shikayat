# Shikayat: campus complaints that count

A student reports a campus problem in English, Hinglish or Hindi, optionally with a photo.
**Gemma 4** buckets it, summarises it, works out whether it is already open, merges duplicates,
and **asks the student back** when something an authority actually needs is missing.
A public board ranks issues by how many students are hitting them; each authority sees only its own queue.

> Complaint portals already exist. They make you fill forms and bury wardens in duplicates.
> Ours takes a Hinglish rant or a photo, works out whether it's already been reported, and asks back when it's unsure.

<!-- P5: replace with docs/screenshot.png once the UI is up -->
![screenshot](docs/screenshot.png)

## The model

`gemma-4-26b-a4b-it`, through the Gemini API. Every call in the project goes through one helper,
`gemma_client.generate_raw`:

```python
# gemma_client.py
_client.models.generate_content(model=MODEL, contents=contents, config=config)
#                               MODEL = "gemma-4-26b-a4b-it"
```

## How to run

```bash
python -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env            # then put your key after GEMINI_API_KEY=
                                # free key: https://aistudio.google.com

./.venv/bin/python -m api.seed --reset           # load seed data into data/shikayat.db
./.venv/bin/uvicorn api.main:app --reload        # API on http://localhost:8000
cd web && npm install && npm run dev             # UI on http://localhost:5173
```

One complaint, straight from the terminal:

```bash
./.venv/bin/python -m complaints.cli "aaj lunch mein dal mein keeda tha" --photo demo/photos/food.jpg
./.venv/bin/python -m complaints.cli "AC se paani tapak raha hai"        # Gemma asks which hostel and room
```

Tests: `./.venv/bin/python -m pytest harness` (no key and no internet needed — it uses a fake model).

## What we changed in the harness and why

*(P1 fills this in — brief section 5. Per-agent tool sets, image input, terminal tools,
pause-for-a-human, step labels, `RunResult`. Two Gemma calls per complaint instead of four.)*

## Architecture

```
React (Vite)  --/api-->  FastAPI (api/)  -->  complaints/agent.py  -->  harness/Agent  -->  Gemma 4 (Gemini API)
     ^                       |                       | tools
     +---- JSON -------------+                       v
                             +-->  SQLite (data/shikayat.db)  <--  complaints/tools.py (via api/db.py)
photos: uploads/<uuid>.jpg, served at /uploads/...
```

## Team

*(P5: names here, and in LICENSE)*

## AI tools disclosure

MLH asks teams to disclose the AI tools they used. We used **Claude Code** (Anthropic) while
building this, alongside the Gemma 4 model that powers the product itself. Lighter assistants
were used by some team members for their own files. All design decisions, the brief, the
harness upgrades and the prompt rules are ours.

## License

MIT — see [LICENSE](LICENSE).
