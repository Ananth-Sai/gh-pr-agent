from pydantic import BaseModel, Field


class SecurityFinding(BaseModel):
    path: str = Field(description="Relative file path where the security issue occurs")
    line: int = Field(description="The exact target line number in the diff")
    severity: str = Field(
        description="Severity level: 'CRITICAL', 'HIGH', 'MEDIUM', or 'LOW'"
    )
    category: str = Field(
        description="Vulnerability category: 'SECRET_LEAK', 'INJECTION', 'AUTH_BYPASS', 'INSECURE_DEPENDENCY', 'UNSAFE_DESERIALIZATION', or 'OTHER'"
    )
    description: str = Field(
        description="Clear explanation of the vulnerability and risk"
    )
    remediation: str | None = Field(
        default=None,
        description="Remediation steps or secure code snippet to resolve the issue",
    )


class SecurityCriticReport(BaseModel):
    summary: str = Field(
        description="High-level overview of the security audit findings"
    )
    has_blocking_vulnerabilities: bool = Field(
        description="True if any CRITICAL or HIGH severity security vulnerability was identified, False otherwise"
    )
    findings: list[SecurityFinding] = Field(
        default_factory=list,
        description="List of specific security vulnerabilities detected in the diff",
    )


class QualityFinding(BaseModel):
    path: str = Field(description="Relative file path where the quality issue occurs")
    line: int = Field(description="The exact target line number in the diff")
    category: str = Field(
        description="Quality category: 'LOGIC_BUG', 'PERFORMANCE', 'STYLE', 'NAMING', 'TYPE_SAFETY', or 'DEAD_CODE'"
    )
    severity: str = Field(
        description="Severity level: 'WARNING', 'SUGGESTION', or 'INFO'"
    )
    description: str = Field(
        description="Clear explanation of the logic flaw, code health issue, or suggestion"
    )
    suggested_patch: str | None = Field(
        default=None,
        description="Recommended replacement code snippet, if applicable",
    )


class QualityCriticReport(BaseModel):
    summary: str = Field(
        description="High-level summary of code quality, correctness, and maintainability"
    )
    findings: list[QualityFinding] = Field(
        default_factory=list,
        description="List of specific code quality, logic, or stylistic observations",
    )


class CriticsEvaluation(BaseModel):
    security_report: SecurityCriticReport = Field(
        description="Output from the specialized Security Critic"
    )
    quality_report: QualityCriticReport = Field(
        description="Output from the specialized Quality Critic"
    )

