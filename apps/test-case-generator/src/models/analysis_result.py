"""Pydantic models for Phase 4 analysis results."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class AnalysisResult(BaseModel):
    """Investigation metadata produced by the test-case-generator agent in Phase 4.

    Written to analysis-results.json in the run directory. This file is for
    auditing and debugging — it is not consumed by downstream pipeline stages.
    """
    jira_id: str
    jira_summary: str
    acm_version: str
    area: str
    pr_number: Optional[int] = None
    pr_repo: str = "stolostron/console"
    test_case_file: str = "test-case.md"
    steps_count: int = 0
    complexity: Literal["low", "medium", "high"] = "medium"
    routes_discovered: list[str] = Field(default_factory=list)
    translations_discovered: dict[str, str] = Field(default_factory=dict)
    selectors_discovered: list[str] = Field(default_factory=list)
    existing_polarion_coverage: list[str] = Field(default_factory=list)
    live_validation_performed: bool = False
    self_review_verdict: Literal["PASS", "FAIL"] = "PASS"
    self_review_issues: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
