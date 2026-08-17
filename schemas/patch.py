from pydantic import BaseModel, Field


class PatchedFile(BaseModel):
    path: str = Field(description="Relative file path being patched")
    content: str = Field(
        description="The complete, corrected source code for this file"
    )


class PatchResponse(BaseModel):
    commit_message: str = Field(
        description="Clear git commit message explaining the fix"
    )
    pr_body: str = Field(
        description="Markdown explanation of what was fixed and why"
    )
    files: list[PatchedFile] = Field(
        description="List of files with their complete fixed source content"
    )
