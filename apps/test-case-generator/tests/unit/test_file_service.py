"""Tests for file_service.py peer test case discovery and knowledge loading."""

from pathlib import Path

import pytest

from src.services.file_service import (
    find_existing_test_cases,
    get_app_root,
    get_knowledge_dir,
    read_area_knowledge,
    read_conventions,
    read_html_templates,
)


class TestKnowledgeLoading:
    def test_conventions_file_exists(self):
        content = read_conventions()
        assert len(content) > 0
        assert "RHACM4K" in content or "Polarion" in content

    def test_html_templates_file_exists(self):
        content = read_html_templates()
        assert len(content) > 0

    def test_governance_knowledge_exists(self):
        content = read_area_knowledge("governance")
        assert content is not None
        assert "Governance" in content

    def test_nonexistent_area_returns_none(self):
        content = read_area_knowledge("nonexistent-area-xyz")
        assert content is None

    def test_all_documented_areas_have_knowledge(self):
        areas = ["governance", "rbac", "fleet-virt", "clusters", "search", "applications", "credentials"]
        for area in areas:
            content = read_area_knowledge(area)
            assert content is not None, f"Missing knowledge file for area: {area}"
            assert len(content) > 100, f"Knowledge file for {area} is too short ({len(content)} chars)"


class TestPeerDiscovery:
    def test_sample_test_case_always_found(self):
        """On a fresh clone, the sample test case should always be found."""
        # Use a version that won't match any external paths
        results = find_existing_test_cases("99.99", area="governance")
        sample_found = any("sample-test-case.md" in r for r in results)
        assert sample_found, "Sample test case not found in knowledge/examples/"

    def test_area_parameter_accepted(self):
        results = find_existing_test_cases("2.17", area="governance")
        assert isinstance(results, list)

    def test_max_count_respected(self):
        results = find_existing_test_cases("2.17", area="governance", max_count=1)
        assert len(results) <= 1

    def test_no_area_still_works(self):
        results = find_existing_test_cases("2.17")
        assert isinstance(results, list)


class TestAppRoot:
    def test_app_root_exists(self):
        root = get_app_root()
        assert root.exists()
        assert (root / "CLAUDE.md").exists()

    def test_knowledge_dir_exists(self):
        kdir = get_knowledge_dir()
        assert kdir.exists()
        assert (kdir / "conventions").exists()
        assert (kdir / "architecture").exists()
        assert (kdir / "examples").exists()
