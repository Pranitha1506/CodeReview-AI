
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class CodeSubmission(BaseModel):
    code: str = Field(..., min_length=1)
    language: str


class CodeReviewResponse(BaseModel):
    overall_score: Optional[int] = None
    summary: str

    bugs: List[dict] = Field(default_factory=list)

    security_issues: List[dict] = Field(default_factory=list)

    optimizations: List[dict] = Field(default_factory=list)

    code_quality: str

    improved_code: str

    source: Literal[
        "Gemini AI",
        "Offline Static Analyzer"
    ] = "Gemini AI"


class CodeFixRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: str


class CodeChange(BaseModel):
    title: str
    explanation: str
    change_type: str


class DiffLine(BaseModel):
    type: Literal["unchanged", "added", "removed"]
    line_number: int
    content: str


class CodeFixResponse(BaseModel):
    language: str

    original_code: str
    fixed_code: str

    decision: Literal[
        "NO_FIX_NEEDED",
        "IMPROVEMENT",
        "BUG_FIX_REQUIRED"
    ]

    decision_reason: str

    syntax_valid: Optional[bool] = None
    syntax_message: str

    summary: str

    changes: List[CodeChange] = Field(default_factory=list)

    remaining_issues: List[str] = Field(default_factory=list)

    testing_notes: List[str] = Field(default_factory=list)

    diff: List[DiffLine] = Field(default_factory=list)

    source: Literal[
        "Gemini AI",
        "Offline Static Analyzer"
    ]

    model_used: Optional[str] = None
