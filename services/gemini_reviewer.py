import logging
from google import genai
from config import GEMINI_API_KEY
from schemas.review import PRReviewResult
from services.gemini_critics import run_critics_in_parallel
from services.gemini_synthesizer import synthesize_reviews

logger = logging.getLogger("gh-pr-agent.reviewer")


def review_pr_diff(
    pr_title: str,
    diff_text: str,
    client: genai.Client | None = None,
) -> PRReviewResult:
    """Orchestrates the multi-agent PR review pipeline:

    1. Fans out concurrent evaluations to specialized Security & Quality Critics.
    2. Gathers and reconciles critic reports via the Lead Review Synthesizer.
    3. Enforces deterministic security gatekeeping and comment deduplication.
    """
    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)

    logger.info(f"Initiating multi-agent review pipeline for PR: '{pr_title}'")

    # Step 1: Concurrent fan-out evaluation
    critics_evaluation = run_critics_in_parallel(pr_title, diff_text, client=client)
    logger.info(
        f"Critics fan-out complete: "
        f"Security findings: {len(critics_evaluation.security_report.findings)} "
        f"(blocking={critics_evaluation.security_report.has_blocking_vulnerabilities}) | "
        f"Quality findings: {len(critics_evaluation.quality_report.findings)}"
    )

    # Step 2: Synthesis and conflict resolution
    final_review = synthesize_reviews(
        pr_title=pr_title,
        diff_text=diff_text,
        evaluation=critics_evaluation,
        client=client,
    )
    logger.info(
        f"Synthesis complete: approved={final_review.approved} | "
        f"total comments={len(final_review.comments)}"
    )

    return final_review
