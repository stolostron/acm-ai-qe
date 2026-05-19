"""Tests for review_enforcement.py scoped verification and MCP counting."""

import importlib.util
import textwrap
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[4] / ".claude" / "skills" / "acm-test-case-generator" / "scripts" / "review_enforcement.py"

spec = importlib.util.spec_from_file_location("review_enforcement", SCRIPT_PATH)
enforcement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(enforcement)


VALID_REVIEW = textwrap.dedent("""\
    TEST CASE REVIEW
    ================
    File: test-case.md
    Area: governance
    Version: 2.17

    MCP VERIFICATIONS
    1. search_translations -- query: "policy.table.labels", result: "Labels", matches: yes
    2. get_routes -- query: "governance", result: "/multicloud/governance/...", matches: yes
    3. get_component_source -- path: "PolicyDetails.tsx", claim: field order, matches: yes

    BLOCKING (must fix):
    None

    WARNING (should fix):
    None

    Verdict: PASS
""")


class TestCountMcpVerifications:
    def test_standard_format(self):
        assert enforcement.count_mcp_verifications(VALID_REVIEW) == 3

    def test_backtick_wrapped(self):
        review = VALID_REVIEW.replace("search_translations", "`search_translations`")
        assert enforcement.count_mcp_verifications(review) >= 1

    def test_zero_verifications(self):
        review = "MCP VERIFICATIONS\n\nBLOCKING:\nNone\nVerdict: PASS"
        assert enforcement.count_mcp_verifications(review) == 0

    def test_missing_section(self):
        review = "Verdict: PASS"
        assert enforcement.count_mcp_verifications(review) == 0


class TestScopedSourceVerification:
    def test_source_in_mcp_section(self):
        assert enforcement.check_source_verification(VALID_REVIEW) is True

    def test_source_only_in_blocking(self):
        review = textwrap.dedent("""\
            MCP VERIFICATIONS
            1. search_translations -- query: "policy", result: "Labels", matches: yes
            2. get_routes -- query: "governance", result: "/multicloud/governance", matches: yes

            BLOCKING (must fix):
            1. get_component_source shows field order mismatch

            Verdict: NEEDS_FIXES
        """)
        assert enforcement.check_source_verification(review) is False

    def test_source_missing_entirely(self):
        review = textwrap.dedent("""\
            MCP VERIFICATIONS
            1. search_translations -- query: "policy", result: found, matches: yes

            BLOCKING:
            None
            Verdict: PASS
        """)
        assert enforcement.check_source_verification(review) is False


class TestScopedTranslationVerification:
    def test_translation_in_mcp_section(self):
        assert enforcement.check_translation_verification(VALID_REVIEW) is True

    def test_translation_only_in_warning(self):
        review = textwrap.dedent("""\
            MCP VERIFICATIONS
            1. get_routes -- query: "governance", result: "/multicloud/governance", matches: yes
            2. get_component_source -- path: "PolicyDetails.tsx", claim: field order, matches: yes

            WARNING (should fix):
            1. search_translations should be used for label verification

            Verdict: NEEDS_FIXES
        """)
        assert enforcement.check_translation_verification(review) is False


class TestExtractVerdict:
    def test_pass(self):
        assert enforcement.extract_verdict(VALID_REVIEW) == "PASS"

    def test_needs_fixes(self):
        assert enforcement.extract_verdict("Verdict: NEEDS_FIXES") == "NEEDS_FIXES"

    def test_unknown(self):
        assert enforcement.extract_verdict("No verdict here") == "UNKNOWN"
