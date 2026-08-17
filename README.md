# 🤖 Autonomous AI PR Review & ChatOps Agent

An event-driven, production-hardened GitHub assistant built with FastAPI, Google Gemini, and Docker. It autonomously audits pull requests, flags vulnerabilities with sticky inline diff comments, generates one-click remediation pull requests, and responds interactively to developer commands directly within PR discussions.

---

## 🌟 Key Features

- **🛡️ Multi-Layer Security Engine:**
  - **Local Pre-Flight Secret Scanner:** Zero-latency regex entropy detection for exposed AWS, OpenAI, and GitHub tokens before making external LLM calls.
  - **Prompt Injection Boundary Isolation:** Encloses untrusted PR titles, diffs, and comments inside strict XML boundaries (`<untrusted_diff>`) to neutralize malicious system override attempts.
  - **HMAC SHA-256 Webhook Verification:** Verifies GitHub webhook authenticity to prevent payload tampering and unauthorized triggers.

- **⚡ Automated Code Review & Sticky Line Validation:**
  - Analyzes unified diff hunks and maps suggestions strictly to valid additions (`RIGHT` side line offsets) to prevent GitHub `422 Unprocessable Entity` API rejections.
  - Emits GitHub-native Markdown suggestions (` ```suggestion``` `) enabling single-click merges.

- **🛠️ Autonomous Remediation Engine:**
  - Automatically creates fix branches (`ai-fix/pr-{id}`) and opens companion remediation pull requests when critical bugs or vulnerabilities are detected.

- **💬 PR ChatOps Assistant:**
  - Intercepts developer commands tagged with `@pr-bot` directly on PR threads to generate unit tests, explain complexity, or suggest alternative implementations.

- **🚀 Resilient Production Architecture:**
  - **Non-Blocking Execution:** Offloads slow LLM and GitHub API operations to asynchronous background tasks, returning instant `200 OK` responses to GitHub.
  - **Dual-Mode Queue:** Enqueues jobs to Redis Queue (`rq`) in production with graceful fallback to in-memory `BackgroundTasks` for local development.
  - **Exponential Backoff:** Built-in retry engine with jitter for handling transient upstream network blips and API rate limits.
  - **Rate Limit Monitoring:** Tracks `X-RateLimit-Remaining` on all GitHub REST operations to prevent service halts.

---

## 🏗️ Architecture & Request Lifecycle

```text
GitHub Webhook (PR Open / Comment)
           │
           ▼
FastAPI App (`routers/webhook.py`)
           │── 1. HMAC SHA-256 Signature Check
           │── 2. Fast 200 OK Acknowledgment
           │
           ▼
Task Dispatcher (`services/queue.py`) ──► [Redis / In-Memory Queue]
           │
    ┌──────┴──────────────────────────────────────────────┐
    │                                                      │
[PR Review Flow]                                    [ChatOps Flow]
    │                                                      │
    ├─► `services/security.py` (Local Secret Scan)         ├─► `services/diff_cleaner.py`
    ├─► `services/diff_cleaner.py` (Noise & Line Filter)    └─► `services/gemini_chatops.py`
    ├─► `services/gemini_reviewer.py` (Audit Engine)               │
    ├─► `services/github_client.py` (Post Review)                  └─► `services/github_client.py`
    └─► `services/gemini_patcher.py` (Auto-Fix PR)                     (Post PR Comment)
```

---

## 📂 Project Structure

```text
gh-pr-agent/
├── config.py                  # Global settings, logging config & environment variables
├── Dockerfile                 # Multi-stage production container
├── main.py                    # Application entrypoint & router mounting
├── requirements.txt           # Pinned dependencies
├── routers/
│   └── webhook.py             # Webhook route handlers & event routing
├── schemas/
│   ├── patch.py               # Pydantic data schemas for patches
│   └── review.py              # Pydantic data schemas for review comments
├── services/
│   ├── diff_cleaner.py        # Noise filtering, lockfile stripper & hunk parser
│   ├── gemini_chatops.py      # Gemini ChatOps interaction logic
│   ├── gemini_patcher.py      # Automated patch generation logic
│   ├── gemini_reviewer.py     # AI code auditor engine
│   ├── github_client.py       # GitHub REST API client with rate-limit tracking
│   ├── queue.py               # Dual-mode persistent task queue dispatcher
│   ├── retry.py               # Exponential backoff decorator with jitter
│   └── security.py            # Local credential and secret scanner
└── tests/
    ├── test_diff_cleaner.py   # Unit tests for diff filtering
    ├── test_queue.py          # Unit tests for queue fallbacks
    ├── test_retry.py          # Unit tests for retry backoff
    ├── test_security.py       # Unit tests for credential patterns
    └── test_webhook.py        # Integration tests for HMAC verification & routes
```

---

## 🧪 Testing

Run the automated test suite with pytest:

```bash
python -m pytest -v
```

---

## ⚙️ Setup & Running Locally

### 1. Local environment setup

```bash
# Clone the repository
git clone https://github.com/Ananth-Sai/gh-pr-bot-test.git
cd gh-pr-agent

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment configuration

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_gemini_api_key
GITHUB_TOKEN=your_github_personal_access_token
WEBHOOK_SECRET=your_webhook_secret_string
REDIS_URL=redis://localhost:6379/0  # Optional (falls back to in-memory mode)
```

### 3. Start application

**Option A: Local server**

```bash
uvicorn main:app --reload --port 8000
```

**Option B: Docker container**

```bash
docker build -t gh-pr-agent .
docker run -p 8000:8000 --env-file .env gh-pr-agent
```

### 4. Configure webhook & forwarding

Forward payloads locally via Smee.io:

```bash
smee --url https://smee.io/<your-channel-id> --target http://127.0.0.1:8000/webhook
```

**GitHub repository webhook settings** (`Settings > Webhooks > Add webhook`):

- **Payload URL:** `https://smee.io/<your-channel-id>` (or your production URL `/webhook`)
- **Content type:** `application/json`
- **Secret:** matches `WEBHOOK_SECRET` from `.env`
- **Events to trigger:** Pull requests, Issue comments
