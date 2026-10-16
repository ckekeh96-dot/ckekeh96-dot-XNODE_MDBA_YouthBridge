# Deployment readiness — YouthBridge v7.4

**Status: LOCAL DEMONSTRATION ONLY — NO-GO for real student data or public deployment.**

## Verified by automated checks
- Local server responds, registration and authentication work
- Sponsor link confirmation is single-use and gates submission
- Student account export and deletion; CSRF checks on account actions
- Mentor feedback authorization and admin role separation
- Security-related response headers and optional Secure session cookie

## Required before a controlled external pilot
1. Formal safeguarding and privacy review appropriate to jurisdiction and ages
2. Verified adult identity and legally appropriate guardian consent, plus revocation workflow
3. HTTPS behind a reviewed reverse proxy, `YB_SECURE_COOKIES=1`, hardened CSP
4. Persistent per-account/IP rate limits and security monitoring; SMTP abuse controls
5. Privacy notice, retention schedule, incident response, account recovery, backups
6. Replace SQLite demo approach with a reviewed production datastore and migrations
7. Accessibility audit, browser/device QA, penetration test, load test
8. Human moderation, escalation/reporting mechanisms, safe contact policy
9. Confirm permission to use any organizer names, logos or official claims

## Local demo launch
`python server.py` then visit http://127.0.0.1:8080/
`python test_pilot.py && python test_safety.py && python test_qa.py`

Never set YB_PUBLIC_BASE_URL to a publicly accessible host without completing the above checks.

## Controlled local demonstration additions
- `run_demo.py` preflights required files and loopback port availability.
- `smoke_test.py` checks local HTTP routes.
- `JUDGE_GUIDE.md` / `.html` document a timed walkthrough.
- `.env.example` documents optional environment settings.
- These additions **do not** change the NO-GO status for public deployment.
