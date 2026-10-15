<div align="center">

# 🤖 Multi-Agent GitHub PR Review & Auto-Fix System

[![Python](https://img.shields.io/badge/Python-FastAPI-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Gemini API](https://img.shields.io/badge/Google%20Gemini-3.x%20Multi--Agent-4285F4?logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![Redis](https://img.shields.io/badge/Redis-Queue%20(fallback)-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Tests Passing](https://img.shields.io/badge/Pytest-29%2F29%20Passing-44A833?logo=pytest&logoColor=white)](#testing)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](./Dockerfile)
[![License](https://img.shields.io/badge/License-MIT-10B981)](./LICENSE)

<p align="center">
  An autonomous multi-agent pipeline that conducts parallel security & quality audits on pull requests,<br/>
  reconciles findings via deterministic lead synthesis, and opens automated fix PRs.
</p>

</div>

---

## See it actually working

This isn't a mock demonstration — these are live, real PRs on a real repository:

- **[PR #6](https://github.com/Ananth-Sai/gh-pr-bot-test/pull/6)** — the agent caught a hardcoded API key, a SQL injection via f-string, and a division-by-zero bug, each with the correct file, correct line, and a real GitHub-native suggested fix.
- **[PR #7](https://github.com/Ananth-Sai/gh-pr-bot-test/pull/7)** — the agent's autonomous remediation engine opened this as a linked fix PR for the issues found in PR #6, without a human writing the patch.
- The agent also responds to `@pr-bot` ChatOps commands directly in PR comments — e.g. `@pr-bot generate pytest unit tests for sample.py` returns a complete, working test suite.

Self-hosted by design — point it at your own repo via a webhook rather than a shared public instance, so it always runs against your own GitHub token and review context.

---

## Multi-Agent Review Architecture

Rather than relying on a single monolithic prompt, this system implements a **three-tier multi-agent pipeline**:

```
                       [Incoming Webhook]
                               │
                      (HMAC Verification)
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       [PR Review Event]              [ChatOps Event]
               │                               │
       (Diff Sanitizer)               (Direct Command)
               │
    ═══════════╪═════════════════════════════════════════════════
               │ Multi-Agent Review Subsystem
               ▼
     [Asynchronous Fan-Out]
        ┌──────┴──────┐
        ▼             ▼
   [Security]     [Quality]
   [ Critic ]     [ Critic ]
   (OWASP/CWE)    (Clean Code)
        └──────┬──────┘
               ▼
     [Lead Review Synthesizer]
        ├─► Deterministic Security Veto Gate (has_blocking_vulnerabilities)
        ├─► Multi-Critic Comment Deduplication (Highest severity wins)
        └─► Structured GitHub Review Payload Generation
    ═══════════╪═════════════════════════════════════════════════
               │
               ▼
       [GitHub REST API]
        ┌──────┴──────┐
        ▼             ▼
    [Inline       [Automated
    Comments]      Patch PR]
```

### 1. Specialized Critic Sub-Agents
- **Security Critic (`gemini_critics.py`):** Strictly audits diffs against OWASP Top 10, CWE patterns, authentication flaws, and injection vectors. Returns structured `SecurityFinding` objects with explicit `is_blocking` flags.
- **Quality Critic (`gemini_critics.py`):** Focuses exclusively on maintainability, cognitive complexity, concurrency pitfalls, and missing edge-case handling. Returns structured `QualityFinding` objects.

### 2. High-Performance Asynchronous Fan-Out
- Both critics execute concurrently in isolated execution contexts via an async thread pool engine (`run_critics_in_parallel`). Total critic latency equals `max(critic_a, critic_b)` rather than their sum.

### 3. Lead Review Synthesizer with Deterministic Veto
- **Zero LLM Rubber-Stamping:** Even if the synthesizing LLM marks a review as approved, a **hard-coded code gate** inspects `security_report.has_blocking_vulnerabilities`. If any blocking vulnerability exists, approval is overridden to `False` deterministically.
- **Comment Deduplication:** Multiple critics commenting on overlapping lines are merged into unified comments, prioritizing the highest severity finding.

---

## Real engineering details worth knowing

- **Secrets are never exposed, even while being reported.** The pre-flight scanner detects GitHub PATs, AWS keys, OpenAI-style keys, Slack tokens, private key blocks, and generic password assignments — but masks every match (`ghp_****...abcd`) before it's logged or sent anywhere. A detected secret's real value never leaves the scanning function.
- **Prompt injection isolation is real, not just a claim.** Diff content is passed to Gemini inside explicit `<untrusted_diff>` XML tags with instructions that anything inside is untrusted input — mitigating a diff that contains "ignore your instructions" style text embedded in a comment or string literal.
- **Line-accurate inline comments.** GitHub's API rejects review comments on lines that aren't part of the diff. This agent pre-computes the exact set of valid target lines per file from the diff hunks before posting, so comments don't silently fail against the API.
- **Resilient Model Fallback Chains.** Every sub-agent and synthesizer call implements a multi-model fallback chain (`gemini-3.5-flash` → `gemini-3.5-flash-lite` → `gemini-3.6-flash`), eliminating rate limits or transient outages as single points of failure.
- **Redis-backed queue with automatic fallback.** If a live Redis instance is reachable, jobs go through a persistent RQ queue with a standalone worker process. If not, it automatically drops to FastAPI's in-memory `BackgroundTasks` — the agent still works with zero extra infrastructure.

---

## Testing

**29 tests, independently run and passing.** The test suite covers critic schemas, specialized agent auditing, asynchronous fan-out, lead synthesis reconciliation, deterministic security vetoes, diff cleaning, secret detection, retry/backoff, queue fallback, and webhook signature verification.

```bash
venv/Scripts/python -m pytest -v
```

Verified output:
```
tests/test_critic_schemas.py::test_security_critic_report_serialization PASSED
tests/test_critic_schemas.py::test_quality_critic_report_serialization PASSED
tests/test_critic_schemas.py::test_empty_reports PASSED
tests/test_critics.py::test_audit_security_success PASSED
tests/test_critics.py::test_audit_quality_success PASSED
tests/test_critics.py::test_critic_model_fallback PASSED
tests/test_critics.py::test_critic_all_models_fail PASSED
tests/test_critics.py::test_run_critics_in_parallel PASSED
tests/test_diff_cleaner.py::test_clean_diff_removes_lockfiles PASSED
tests/test_diff_cleaner.py::test_clean_diff_truncates_large_payloads PASSED
tests/test_diff_cleaner.py::test_get_valid_diff_lines_by_file PASSED
tests/test_queue.py::test_enqueue_task_fallback_to_background_tasks PASSED
tests/test_queue.py::test_enqueue_task_direct_run_without_bg PASSED
tests/test_retry.py::test_retry_eventual_success PASSED
tests/test_retry.py::test_retry_exceeds_max_retries PASSED
tests/test_reviewer_pipeline.py::test_review_pr_diff_pipeline_clean_flow PASSED
tests/test_reviewer_pipeline.py::test_review_pr_diff_pipeline_vulnerable_flow PASSED
tests/test_security.py::test_scan_diff_detects_github_pat PASSED
tests/test_security.py::test_scan_diff_detects_aws_key PASSED
tests/test_security.py::test_scan_diff_detects_openai_key PASSED
tests/test_security.py::test_scan_diff_clean_code PASSED
tests/test_synthesizer.py::test_deduplicate_and_prioritize_comments PASSED
tests/test_synthesizer.py::test_deterministic_security_veto_overrides_llm_approval PASSED
tests/test_synthesizer.py::test_synthesize_clean_approval PASSED
tests/test_synthesizer.py::test_synthesizer_all_models_fail PASSED
tests/test_webhook.py::test_health_check PASSED
tests/test_webhook.py::test_webhook_missing_signature PASSED
tests/test_webhook.py::test_webhook_invalid_signature PASSED
tests/test_webhook.py::test_webhook_valid_signature_accepted PASSED

======================= 29 passed, 2 warnings in 3.87s ========================
```

---

## Tech Stack

- **Backend:** Python 3.12+, FastAPI
- **Multi-Agent Core:** Google Gemini API (`gemini-3.5-flash`, `gemini-3.5-flash-lite`, `gemini-3.6-flash` fallback chain)
- **Data Validation:** Pydantic v2
- **Queue:** Redis + RQ, with automatic in-memory fallback
- **Testing:** Pytest, AnyIO
- **Deployment:** Docker

---

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
BOT_HANDLE=@pr-bot
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

---

## License

MIT
