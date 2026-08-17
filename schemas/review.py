from pydantic import BaseModel, Field


class InlineComment(BaseModel):
    path: str = Field(description="Relative file path where the issue occurs")
    line: int = Field(description="The exact target line number in the new file")
    severity: str = Field(
        description="Severity level: 'CRITICAL', 'WARNING', or 'SUGGESTION'"
    )
    comment: str = Field(
        description="Detailed review feedback and explanation of the issue"
    )
    suggested_patch: str | None = Field(
        default=None,
        description="Exact replacement code snippet or patch, if applicable",
    )


class PRReviewResult(BaseModel):
    summary: str = Field(
        description="High-level markdown summary of the PR and overall verdict"
    )
    approved: bool = Field(
        description="True if PR is safe and clean to merge, False otherwise"
    )
    comments: list[InlineComment] = Field(
        default_factory=list,
        description="List of specific inline comments and suggested changes",
    )
