import json
from schemas.critic import (
    SecurityFinding,
    SecurityCriticReport,
    QualityFinding,
    QualityCriticReport,
)


def test_security_critic_report_serialization():
    finding = SecurityFinding(
        path="auth/jwt.py",
        line=42,
        severity="CRITICAL",
        category="SECRET_LEAK",
        description="Hardcoded private signing key detected.",
        remediation="Move private key to environment variables.",
    )
    report = SecurityCriticReport(
        summary="Found 1 critical secret leak.",
        has_blocking_vulnerabilities=True,
        findings=[finding],
    )

    json_str = report.model_dump_json()
    data = json.loads(json_str)

    assert data["has_blocking_vulnerabilities"] is True
    assert len(data["findings"]) == 1
    assert data["findings"][0]["severity"] == "CRITICAL"
    assert data["findings"][0]["category"] == "SECRET_LEAK"

    # Verify round-trip parsing
    reconstructed = SecurityCriticReport.model_validate_json(json_str)
    assert reconstructed.findings[0].line == 42
    assert reconstructed.findings[0].remediation == "Move private key to environment variables."


def test_quality_critic_report_serialization():
    finding = QualityFinding(
        path="utils/math.py",
        line=15,
        category="LOGIC_BUG",
        severity="WARNING",
        description="Potential division by zero when denominator is 0.",
        suggested_patch="if denom == 0:\n    return 0.0",
    )
    report = QualityCriticReport(
        summary="Code style is fine, but 1 potential edge case logic bug exists.",
        findings=[finding],
    )

    json_str = report.model_dump_json()
    data = json.loads(json_str)

    assert len(data["findings"]) == 1
    assert data["findings"][0]["category"] == "LOGIC_BUG"

    reconstructed = QualityCriticReport.model_validate_json(json_str)
    assert reconstructed.findings[0].suggested_patch == "if denom == 0:\n    return 0.0"


def test_empty_reports():
    sec_report = SecurityCriticReport(
        summary="No security issues identified.",
        has_blocking_vulnerabilities=False,
    )
    assert len(sec_report.findings) == 0
    assert sec_report.has_blocking_vulnerabilities is False

    qual_report = QualityCriticReport(
        summary="Clean code adhering to PEP8.",
    )
    assert len(qual_report.findings) == 0
