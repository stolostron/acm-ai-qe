"""Pydantic models for Stage 3 review results."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class ValidationIssue(BaseModel):
    """A single validation issue found during structural review."""
    severity: str  # "blocking" | "warning" | "suggestion"
    category: str  # "metadata" | "description" | "setup" | "steps" | "teardown" | "title"
    message: str
    line: Optional[int] = None


class ReviewResult(BaseModel):
    """Complete structural review result from Stage 3."""
    test_case_file: str
    verdict: Verdict
    issues: list[ValidationIssue] = Field(default_factory=list)
    metadata_complete: bool = False
    section_order_valid: bool = False
    title_pattern_valid: bool = False
    entry_point_present: bool = False
    jira_coverage_present: bool = False
    step_format_valid: bool = False
    teardown_present: bool = False
    total_steps: int = 0

    @property
    def blocking_issues(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "blocking"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]
