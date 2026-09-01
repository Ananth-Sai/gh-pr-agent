<div align="center">

# 🤖 GitHub PR Review & Auto-Fix Agent

[![Python](https://img.shields.io/badge/Python-FastAPI-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Gemini API](https://img.shields.io/badge/Google-Gemini%203.x-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![Redis](https://img.shields.io/badge/Redis-Queue%20(w%2F%20fallback)-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Tests Passing](https://img.shields.io/badge/Pytest-15%2F15%20Passing-44A833?style=for-the-badge&logo=pytest)](#testing)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](./Dockerfile)
[![License](https://img.shields.io/badge/License-MIT-9945FF?style=for-the-badge)](./LICENSE)

<p align="center">
  An autonomous agent that reviews real pull requests, catches real bugs, and opens real fix PRs —<br/>
  a genuine tool-calling agent loop, not a chatbot wrapper.
</p>

</div>

---

## See it actually working

This isn't a demo video — these are live, real PRs on a real repository:

- **[PR #6](https://github.com/Ananth-Sai/gh-pr-bot-test/pull/6)** — the agent caught a hardcoded API key, a SQL injection via f-string, and a division-by-zero bug, each with the correct file, correct line, and a real GitHub-native suggested fix.
- **[PR #7](https://github.com/Ananth-Sai/gh-pr-bot-test/pull/7)** — the agent's autonomous remediation engine opened this as a linked fix PR for the issues found in PR #6, without a human writing the patch.
- The agent also responds to `@pr-bot` ChatOps commands directly in PR comments — e.g. `@pr-bot generate pytest unit tests for sample.py` returns a complete, working test suite.

Self-hosted by design — point it at your own repo via a webhook rather than a shared public instance, so it always runs against your own GitHub token and review context.

## How it works

```
[Developer Opens PR]
         │
         ▼ (Webhook)
[FastAPI Server] ──► HMAC-SHA256 signature verification
         │
         ├─► Diff cleaning: strips lockfiles/binary assets, truncates oversized diffs
         ├─► Local secret pre-flight scan (masked before it ever leaves the function)
         ├─► Line-map extraction (keeps inline comments on valid diff lines only)
         ├─► Gemini review inside an XML-isolated <untrusted_diff> boundary
         │
         ▼
[GitHub REST API]
         │
    ┌────┴────┐
    ▼         ▼
Inline    Auto-fix
comments   patch PR
```

## Real engineering details worth knowing

- **Secrets are never actually exposed, even while being reported.** The pre-flight scanner detects GitHub PATs, AWS keys, OpenAI-style keys, Slack tokens, private key blocks, and generic password assignments — but masks every match (`ghp_****...abcd`) before it's logged or sent anywhere. A detected secret's real value never leaves the scanning function.
- **Prompt injection isolation is real, not just a claim.** Diff content is passed to Gemini inside explicit `<untrusted_diff>` XML tags with instructions that anything inside is untrusted input — mitigating a diff that contains "ignore your instructions" style text embedded in a comment or string literal.
- **Line-accurate inline comments.** GitHub's API rejects review comments on lines that aren't part of the diff. This agent pre-computes the exact set of valid target lines per file from the diff hunks before posting, so comments don't silently fail against the API.
- **Redis-backed queue with real fallback, not a fake one.** If a live Redis instance is reachable, jobs go through a persistent RQ queue with a standalone worker process. If not, it automatically drops to FastAPI's in-memory `BackgroundTasks` — the agent still works with zero extra infrastructure, just without job persistence across restarts.

## Testing

15 tests, independently run and passing — covering diff cleaning (lockfile filtering, truncation), secret detection (GitHub PAT, AWS key, OpenAI key, and a clean-code negative case), retry/backoff behavior, queue fallback logic, and webhook signature validation (missing signature, invalid signature, and valid signature acceptance).

```bash
pytest tests/ -v
```

## Tech Stack

- **Backend:** Python, FastAPI
- **AI:** Google Gemini API (`gemini-3.5-flash` / `gemini-3.5-flash-lite` / `gemini-3.6-flash`, with fallback across all three)
- **Queue:** Redis + RQ, with automatic in-memory fallback
- **Testing:** Pytest
- **Deployment:** Docker

## Self-Hosting Setup

### 1. Clone and install
```bash
git clone https://github.com/Ananth-Sai/gh-pr-agent.git
cd gh-pr-agent
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
```

### 2. Environment variables

Copy `.env.example` to `.env`:
```
GITHUB_TOKEN=your_github_personal_access_token
WEBHOOK_SECRET=choose_a_random_secret_string
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Run locally with a tunnel

```bash
uvicorn main:app --reload
```

Use `smee.io` or `ngrok` to tunnel your local server, then configure the webhook (with your `WEBHOOK_SECRET`) on the target repo's GitHub settings, pointed at `/webhook`.

### 4. (Optional) Run the persistent worker

If you have Redis running locally, start the standalone worker for persistent job queueing:
```bash
python worker.py
```
Without Redis, the agent still works — it just falls back to in-memory task handling automatically.

### 5. Or deploy with Docker

```bash
docker build -t gh-pr-agent .
docker run -p 8000:8000 --env-file .env gh-pr-agent
```

## License

MIT
