from unittest.mock import MagicMock
import pytest
from schemas.critic import (
    CriticsEvaluation,
    SecurityCriticReport,
    SecurityFinding,
    QualityCriticReport,
    QualityFinding,
)
from schemas.review import InlineComment, PRReviewResult
from services.gemini_synthesizer import (
    deduplicate_and_prioritize_comments,
    synthesize_reviews,
)


def test_deduplicate_and_prioritize_comments():
    comments = [
        InlineComment(
            path="db/query.py",
            line=20,
            severity="SUGGESTION",
            comment="Format query on multiple lines.",
        ),
        InlineComment(
            path="db/query.py",
            line=20,
            severity="CRITICAL",
            comment="SQL Injection: query constructed via string concatenation.",
            suggested_patch="cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
        ),
        InlineComment(
            path="utils/helper.py",
            line=10,
            severity="WARNING",
            comment="Unused import math.",
        ),
    ]

    deduped = deduplicate_and_prioritize_comments(comments)
    assert len(deduped) == 2

    # Verify query.py line 20 kept the CRITICAL security finding, discarding SUGGESTION
    query_comment = next(c for c in deduped if c.path == "db/query.py")
    assert query_comment.severity == "CRITICAL"
    assert "SQL Injection" in query_comment.comment
    assert query_comment.suggested_patch is not None


def test_deterministic_security_veto_overrides_llm_approval():
    """Even if LLM erroneously outputs approved=True, blocking security vulnerabilities force approved=False."""
    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_client.chats.create.return_value = mock_chat

    # LLM hallucinates an approval
    mock_response = MagicMock()
    mock_response.text = (
        '{"summary": "LGTM! Approved.", "approved": true, "comments": []}'
    )
    mock_chat.send_message.return_value = mock_response

    evaluation = CriticsEvaluation(
        security_report=SecurityCriticReport(
            summary="Critical leaked token found",
            has_blocking_vulnerabilities=True,
            findings=[
                SecurityFinding(
                    path="config.py",
                    line=5,
                    severity="CRITICAL",
                    category="SECRET_LEAK",
                    description="Exposed API token",
                )
            ],
        ),
        quality_report=QualityCriticReport(
            summary="Clean formatting",
            findings=[],
        ),
    )

    result = synthesize_reviews("feat: add config", "+TOKEN=12345", evaluation, client=mock_client)
    assert isinstance(result, PRReviewResult)
    # The deterministic safeguard in synthesize_reviews must veto LLM approval
    assert result.approved is False


def test_synthesize_clean_approval():
    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_client.chats.create.return_value = mock_chat

    mock_response = MagicMock()
    mock_response.text = (
        '{"summary": "Code looks great and secure.", "approved": true, "comments": []}'
    )
    mock_chat.send_message.return_value = mock_response

    evaluation = CriticsEvaluation(
        security_report=SecurityCriticReport(
            summary="No security findings",
            has_blocking_vulnerabilities=False,
            findings=[],
        ),
        quality_report=QualityCriticReport(
            summary="Clean structure",
            findings=[],
        ),
    )

    result = synthesize_reviews("feat: clean feature", "+def add(a, b): return a + b", evaluation, client=mock_client)
    assert result.approved is True
    assert "Code looks great" in result.summary


def test_synthesizer_all_models_fail():
    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_chat.send_message.side_effect = Exception("Model quota exhausted")
    mock_client.chats.create.return_value = mock_chat

    evaluation = CriticsEvaluation(
        security_report=SecurityCriticReport(summary="", has_blocking_vulnerabilities=False),
        quality_report=QualityCriticReport(summary=""),
    )

    with pytest.raises(RuntimeError, match="All configured synthesizer models failed"):
        synthesize_reviews("title", "+diff", evaluation, client=mock_client)
