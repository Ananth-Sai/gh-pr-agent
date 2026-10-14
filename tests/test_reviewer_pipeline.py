from unittest.mock import MagicMock
from schemas.critic import (
    CriticsEvaluation,
    SecurityCriticReport,
    SecurityFinding,
    QualityCriticReport,
    QualityFinding,
)
from schemas.review import InlineComment, PRReviewResult
from services.gemini_reviewer import review_pr_diff


def test_review_pr_diff_pipeline_clean_flow(monkeypatch):
    """End-to-end integration test for clean PR: Critics clear, synthesizer approves."""
    mock_client = MagicMock()

    mock_security = SecurityCriticReport(
        summary="No security vulnerabilities identified.",
        has_blocking_vulnerabilities=False,
        findings=[],
    )
    mock_quality = QualityCriticReport(
        summary="Code style and logic are clean.",
        findings=[],
    )

    monkeypatch.setattr(
        "services.gemini_reviewer.run_critics_in_parallel",
        lambda pr_title, diff_text, client=None: CriticsEvaluation(
            security_report=mock_security,
            quality_report=mock_quality,
        ),
    )

    mock_synthesized = PRReviewResult(
        summary="### Review Summary\n\n- Security: Clean\n- Quality: Clean\nVerdict: Approved.",
        approved=True,
        comments=[],
    )
    monkeypatch.setattr(
        "services.gemini_reviewer.synthesize_reviews",
        lambda pr_title, diff_text, evaluation, client=None: mock_synthesized,
    )

    result = review_pr_diff(
        pr_title="feat: add user profile endpoint",
        diff_text="diff --git a/app.py b/app.py\n+def get_user(): return {'id': 1}",
        client=mock_client,
    )

    assert isinstance(result, PRReviewResult)
    assert result.approved is True
    assert len(result.comments) == 0
    assert "Approved" in result.summary


def test_review_pr_diff_pipeline_vulnerable_flow(monkeypatch):
    """End-to-end integration test for vulnerable PR: Security blocks merge, comments reconciled."""
    mock_client = MagicMock()

    mock_security = SecurityCriticReport(
        summary="Found 1 critical secret leak.",
        has_blocking_vulnerabilities=True,
        findings=[
            SecurityFinding(
                path="config.py",
                line=12,
                severity="CRITICAL",
                category="SECRET_LEAK",
                description="Hardcoded API secret key detected.",
                remediation="Read secret from os.environ.",
            )
        ],
    )
    mock_quality = QualityCriticReport(
        summary="Code style has minor formatting issues.",
        findings=[
            QualityFinding(
                path="config.py",
                line=12,
                category="STYLE",
                severity="SUGGESTION",
                description="Add type annotation to secret variable.",
            )
        ],
    )

    monkeypatch.setattr(
        "services.gemini_reviewer.run_critics_in_parallel",
        lambda pr_title, diff_text, client=None: CriticsEvaluation(
            security_report=mock_security,
            quality_report=mock_quality,
        ),
    )

    # The synthesizer creates the reconciled review with security finding overriding style suggestion
    mock_synthesized = PRReviewResult(
        summary="### Review Summary\n\nSecurity vulnerability detected: hardcoded secret.",
        approved=False,
        comments=[
            InlineComment(
                path="config.py",
                line=12,
                severity="CRITICAL",
                comment="Hardcoded API secret key detected. Read from os.environ.",
                suggested_patch="API_KEY = os.getenv('API_KEY')",
            )
        ],
    )
    monkeypatch.setattr(
        "services.gemini_reviewer.synthesize_reviews",
        lambda pr_title, diff_text, evaluation, client=None: mock_synthesized,
    )

    result = review_pr_diff(
        pr_title="feat: add external service config",
        diff_text="diff --git a/config.py b/config.py\n+API_KEY = 'sk-12345'",
        client=mock_client,
    )

    assert isinstance(result, PRReviewResult)
    assert result.approved is False
    assert len(result.comments) == 1
    assert result.comments[0].severity == "CRITICAL"
    assert result.comments[0].path == "config.py"
    assert result.comments[0].line == 12
