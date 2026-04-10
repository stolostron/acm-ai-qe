"""Pydantic models for Stage 1 gather output."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PRData(BaseModel):
    """Pull request data gathered via gh CLI."""
    number: int
    title: str
    repo: str = "stolostron/console"
    state: str = "merged"
    body: Optional[str] = None
    files: list[str] = Field(default_factory=list)
    additions: int = 0
    deletions: int = 0
    merged_at: Optional[str] = None
    diff_file: Optional[str] = None


class GatherOptions(BaseModel):
    """Pipeline options from CLI arguments."""
    skip_live: bool = False
    repo: str = "stolostron/console"


class GatherOutput(BaseModel):
    """Complete output from Stage 1 gather."""
    jira_id: str
    acm_version: Optional[str] = None
    area: Optional[str] = None
    pr_data: Optional[PRData] = None
    existing_test_cases: list[str] = Field(default_factory=list)
    conventions: str = ""
    area_knowledge: Optional[str] = None
    html_templates: str = ""
    run_dir: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    options: GatherOptions = Field(default_factory=GatherOptions)
