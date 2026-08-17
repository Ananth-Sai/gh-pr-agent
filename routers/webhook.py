import hashlib
import hmac
import logging
import os
import re
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
import requests

from config import BOT_HANDLE, GITHUB_TOKEN, WEBHOOK_SECRET
from services.diff_cleaner import clean_and_truncate_diff, get_valid_diff_lines_by_file
from services.gemini_chatops import answer_pr_command
from services.gemini_patcher import generate_patch
from services.gemini_reviewer import review_pr_diff
from services.github_client import (
    create_patch_branch_and_pr,
    post_issue_comment,
    submit_formal_pr_review,
)
from services.queue import enqueue_task
from services.security import scan_diff_for_secrets

logger = logging.getLogger("gh-pr-agent.webhook")
router = APIRouter()


def verify_signature(body: bytes, x_hub_signature_256: str) -> None:
    if not WEBHOOK_SECRET:
        logger.error("WEBHOOK_SECRET is not configured.")
        raise HTTPException(status_code=500, detail="WEBHOOK_SECRET not configured")
    if not x_hub_signature_256:
        logger.warning("Missing signature header.")
        raise HTTPException(status_code=403, detail="Missing signature")

    expected = "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, x_hub_signature_256):
        logger.warning("Rejected webhook request with invalid HMAC signature.")
        raise HTTPException(status_code=403, detail="Invalid signature")


def process_pr_review(
    repo_full_name: str,
    pr_number: int,
    title: str,
    source_branch: str,
    head_sha: str,
) -> None:
    pr_tag = f"[PR #{pr_number}]"
    logger.info(f"{pr_tag} Review started for '{title}' (Branch: {source_branch}, SHA: {head_sha[:7]})")

    api_url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
    headers = {"Accept": "application/vnd.github.v3.diff", "User-Agent": "AI-PR-Reviewer-Bot"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    diff_response = requests.get(api_url, headers=headers, timeout=10)
    if diff_response.status_code != 200:
        logger.error(f"{pr_tag} Failed to fetch unified diff from GitHub API (Status: {diff_response.status_code})")
        return

    raw_diff = diff_response.text

    detected_secrets = scan_diff_for_secrets(raw_diff)
    if detected_secrets:
        logger.warning(f"{pr_tag} ⚠️ LOCAL SCAN DETECTED {len(detected_secrets)} EXPOSED SECRET(S) IN DIFF:")
        for s in detected_secrets:
            logger.warning(f"{pr_tag}   -> Type: {s.secret_type} | Snippet: {s.matched_snippet} | Line: {s.line_number}")

    cleaned_diff = clean_and_truncate_diff(raw_diff)
    valid_lines_map = get_valid_diff_lines_by_file(raw_diff)

    logger.info(f"{pr_tag} Dispatching diff to Gemini Reviewer...")
    review = review_pr_diff(title, cleaned_diff)
    logger.info(f"{pr_tag} Review completed. Approved: {review.approved} | Comments: {len(review.comments)}")

    submit_formal_pr_review(
        repo_full_name=repo_full_name,
        pr_number=pr_number,
        commit_id=head_sha,
        review_summary=review.summary,
        is_approved=review.approved,
        comments=review.comments,
        valid_lines_map=valid_lines_map,
    )

    if not review.approved:
        logger.info(f"{pr_tag} PR not approved. Generating automated patch...")
        patch_result = generate_patch(title, cleaned_diff, review.summary)
        create_patch_branch_and_pr(
            repo_full_name=repo_full_name,
            original_pr_number=pr_number,
            base_branch=source_branch,
            commit_msg=patch_result.commit_message,
            pr_description=patch_result.pr_body,
            files=patch_result.files,
        )


def process_chatops_command(
    repo_full_name: str,
    pr_number: int,
    pr_title: str,
    clean_prompt: str,
) -> None:
    chat_tag = f"[ChatOps #{pr_number}]"
    logger.info(f"{chat_tag} Command received: '{clean_prompt}'")

    api_url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pr_number}"
    headers = {"Accept": "application/vnd.github.v3.diff", "User-Agent": "AI-PR-Reviewer-Bot"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    diff_res = requests.get(api_url, headers=headers, timeout=10)
    raw_diff = diff_res.text if diff_res.status_code == 200 else ""
    cleaned_diff = clean_and_truncate_diff(raw_diff)

    ai_reply = answer_pr_command(clean_prompt, pr_title, cleaned_diff)
    post_issue_comment(repo_full_name, pr_number, ai_reply)


@router.post("/webhook")
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
):
    body = await request.body()
    verify_signature(body, x_hub_signature_256)
    payload = await request.json()

    if x_github_event == "issue_comment":
        action = payload.get("action")
        if action != "created":
            return {"status": "ignored", "reason": "Not a new comment."}

        comment_body = payload.get("comment", {}).get("body", "")
        if BOT_HANDLE not in comment_body.lower():
            return {"status": "ignored", "reason": f"Comment does not tag {BOT_HANDLE}."}
        if "*Response generated by @pr-bot*" in comment_body:
            return {"status": "ignored", "reason": "Ignoring bot response."}

        issue = payload.get("issue", {})
        if "pull_request" not in issue:
            return {"status": "ignored", "reason": "Comment is on an Issue, not a PR."}

        pr_number = issue.get("number")
        repo_full_name = payload.get("repository", {}).get("full_name")
        pr_title = issue.get("title")
        clean_prompt = re.sub(rf"{re.escape(BOT_HANDLE)}", "", comment_body, flags=re.IGNORECASE).strip()

        enqueue_task(
            process_chatops_command,
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            pr_title=pr_title,
            clean_prompt=clean_prompt,
            background_tasks=background_tasks,
        )
        return {"status": "accepted", "message": "ChatOps task dispatched."}

    elif x_github_event == "pull_request":
        action = payload.get("action")
        if action not in ["opened", "synchronize", "reopened"]:
            return {"status": "ignored", "reason": f"Action '{action}' ignored."}

        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})
        pr_number = pr.get("number")
        repo_full_name = repo.get("full_name")
        title = pr.get("title")
        source_branch = pr.get("head", {}).get("ref", "master")
        head_sha = pr.get("head", {}).get("sha")

        if source_branch.startswith("ai-fix/"):
            return {"status": "ignored", "reason": "Ignoring bot's own fix PR branch."}

        enqueue_task(
            process_pr_review,
            repo_full_name=repo_full_name,
            pr_number=pr_number,
            title=title,
            source_branch=source_branch,
            head_sha=head_sha,
            background_tasks=background_tasks,
        )
        return {"status": "accepted", "message": "PR review task dispatched."}

    return {"status": "ignored", "reason": f"Unhandled event: {x_github_event}"}