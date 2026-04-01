#!/usr/bin/env python3
"""Tests for KNOWN_REPOS fallback entries."""

import pytest
from src.services.shared_utils import RepositoryConfig


class TestKnownReposAlc:
    """Verify ALC repo entries exist in KNOWN_REPOS fallback."""

    def setup_method(self):
        self.config = RepositoryConfig()

    def test_alc_hyphen_entry(self):
        assert 'alc-e2e' in self.config.KNOWN_REPOS
        assert 'application-ui-test' in self.config.KNOWN_REPOS['alc-e2e']

    def test_alc_underscore_entry(self):
        assert 'alc_e2e' in self.config.KNOWN_REPOS
        assert 'application-ui-test' in self.config.KNOWN_REPOS['alc_e2e']

    def test_application_ui_test_entry(self):
        assert 'application-ui-test' in self.config.KNOWN_REPOS
        assert 'application-ui-test' in self.config.KNOWN_REPOS['application-ui-test']

    def test_app_e2e_entry(self):
        assert 'app-e2e' in self.config.KNOWN_REPOS
        assert 'application-ui-test' in self.config.KNOWN_REPOS['app-e2e']

    def test_all_alc_entries_same_url(self):
        """All ALC aliases must point to the same repo."""
        alc_keys = ['alc-e2e', 'alc_e2e', 'application-ui-test', 'app-e2e']
        urls = {self.config.KNOWN_REPOS[k] for k in alc_keys}
        assert len(urls) == 1, f"ALC entries point to different URLs: {urls}"

    def test_existing_clc_entries_unchanged(self):
        """Existing CLC entries must not be affected."""
        assert 'clc-e2e' in self.config.KNOWN_REPOS
        assert 'clc-ui-e2e' in self.config.KNOWN_REPOS['clc-e2e']

    def test_existing_search_entry_unchanged(self):
        """Existing search entry must not be affected."""
        assert 'search-e2e' in self.config.KNOWN_REPOS
        assert 'search-e2e-test' in self.config.KNOWN_REPOS['search-e2e']


class TestKnownReposFoundation:
    """Verify Foundation/Install repo entries in KNOWN_REPOS."""

    def setup_method(self):
        self.config = RepositoryConfig()

    def test_server_foundation_entry(self):
        assert 'server_foundation' in self.config.KNOWN_REPOS
        assert 'acmqe-autotest' in self.config.KNOWN_REPOS['server_foundation']

    def test_acmqe_autotest_entry(self):
        assert 'acmqe-autotest' in self.config.KNOWN_REPOS
        assert 'acmqe-autotest' in self.config.KNOWN_REPOS['acmqe-autotest']

    def test_install_e2e_entry(self):
        assert 'install_e2e' in self.config.KNOWN_REPOS
        assert 'acmqe-autotest' in self.config.KNOWN_REPOS['install_e2e']

    def test_install_acm_entry(self):
        assert 'install_acm' in self.config.KNOWN_REPOS
        assert 'acmqe-autotest' in self.config.KNOWN_REPOS['install_acm']

    def test_install_mce_entry(self):
        assert 'install_mce' in self.config.KNOWN_REPOS
        assert 'acmqe-autotest' in self.config.KNOWN_REPOS['install_mce']

    def test_all_foundation_install_entries_same_url(self):
        """All Foundation/Install aliases must point to acmqe-autotest."""
        keys = ['server_foundation', 'acmqe-autotest', 'install_e2e',
                'install_acm', 'install_mce']
        urls = {self.config.KNOWN_REPOS[k] for k in keys}
        assert len(urls) == 1, f"Foundation/Install entries point to different URLs: {urls}"


class TestKnownReposGrc:
    """Verify GRC (acmqe-grc-test) repo entries in KNOWN_REPOS."""

    def setup_method(self):
        self.config = RepositoryConfig()

    def test_grc_upgrade_entry(self):
        assert 'grc-upgrade' in self.config.KNOWN_REPOS
        assert 'acmqe-grc-test' in self.config.KNOWN_REPOS['grc-upgrade']

    def test_grc_e2e_entry(self):
        assert 'grc-e2e' in self.config.KNOWN_REPOS
        assert 'acmqe-grc-test' in self.config.KNOWN_REPOS['grc-e2e']

    def test_acmqe_grc_entry(self):
        assert 'acmqe-grc' in self.config.KNOWN_REPOS
        assert 'acmqe-grc-test' in self.config.KNOWN_REPOS['acmqe-grc']

    def test_all_grc_new_entries_same_url(self):
        """All new GRC aliases must point to acmqe-grc-test."""
        keys = ['grc-upgrade', 'grc-e2e', 'acmqe-grc']
        urls = {self.config.KNOWN_REPOS[k] for k in keys}
        assert len(urls) == 1, f"GRC entries point to different URLs: {urls}"

    def test_old_grc_entry_unchanged(self):
        """Old grc-ui-e2e entry must still exist (different repo)."""
        assert 'grc-ui-e2e' in self.config.KNOWN_REPOS
        assert 'grc-ui-e2e' in self.config.KNOWN_REPOS['grc-ui-e2e']


class TestKnownReposRightSizing:
    """Verify Right Sizing / Analytics repo entries in KNOWN_REPOS."""

    def setup_method(self):
        self.config = RepositoryConfig()

    def test_right_sizing_entry(self):
        assert 'right_sizing' in self.config.KNOWN_REPOS
        assert 'acmqe-analytics' in self.config.KNOWN_REPOS['right_sizing']

    def test_acmqe_analytics_entry(self):
        assert 'acmqe-analytics' in self.config.KNOWN_REPOS
        assert 'acmqe-analytics' in self.config.KNOWN_REPOS['acmqe-analytics']

    def test_all_rightsizing_entries_same_url(self):
        """All Right Sizing aliases must point to acmqe-analytics."""
        keys = ['right_sizing', 'acmqe-analytics']
        urls = {self.config.KNOWN_REPOS[k] for k in keys}
        assert len(urls) == 1, f"RightSizing entries point to different URLs: {urls}"
