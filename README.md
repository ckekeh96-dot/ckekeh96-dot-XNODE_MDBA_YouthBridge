# XNODE MDBA YouthBridge v7.5 — Colorful Student Experience

# MDBA YouthBridge v7.4 — Controlled Local Demo

Independent, unofficial education prototype. **Local demonstration only; fictional records only.**

## Quick start (Windows/macOS/Linux)
1. Install Python 3.10+.
2. Run `python run_demo.py` from this directory.
3. Visit `http://127.0.0.1:8080/`.
4. Open `JUDGE_GUIDE.html` for the presentation, or `JUDGE_GUIDE.md` for the editable guide.
5. In another terminal, run `python smoke_test.py`.

## Full test suite
`python test_pilot.py`
`python test_safety.py`
`python test_qa.py`

## Package contents
- `server.py`: local Python/SQLite student, mentor, admin, sponsor-link demo
- `static/practice.html`: guided learning and no-code Practice Lab
- `run_demo.py`: loopback-only startup preflight
- `smoke_test.py`: read-only HTTP checks
- `.env.example`: environment variable reference; not auto-loaded
- `JUDGE_GUIDE.md` and `JUDGE_GUIDE.html`: presentation script, demo data, safety notes
- `DEPLOYMENT_READINESS.md`: public deployment NO-GO checklist

## Limitations
The app is **not** production-ready, and sponsor-link confirmation is **not** identity or guardian consent verification. Do not deploy publicly or collect real minors' data. The local SQLite database is created when first started. See deployment checklist for outstanding security, privacy and accessibility requirements.

## v7.5 design update
- Branded XNODE MDBA YouthBridge across local pilot and Practice Lab.
- Student-friendly landing hero, visual challenge cards, refreshed navigation and accessible focus states.
- Visuals based on the user-selected dashboard reference; images bundled offline in `static/assets`.
- Existing v7.4 account, sponsor, mentor, admin and Practice Lab logic preserved.
- This is a local educational demo, not a production service for real minors.

## v7.6 Reference Dashboard Redesign
- Homepage rebuilt to closely follow the user-supplied visual reference: dark left navigation, large branded top bar, illustrated hero, six bright mission tiles, featured sustainability challenge, four project templates, five-step workflow, progress and inspiration cards.
- All navigation links open the corresponding existing Practice Lab page or local account dashboard. Practice Lab deep links use a validated URL fragment.
- Existing Python student, sponsor, mentor and admin workflows are retained. No fictional leaderboard scores or real community users are fabricated.
- This is a visual adaptation of the reference, not a pixel-identical copy. Existing bundled images are used for the cards and hero.
- Run `python run_demo.py` and visit http://127.0.0.1:8081/ .
