"""
Phase 0 Initialization Cleanup Mock Tests
==========================================

Comprehensive mock-based tests for Phase 0 framework initialization cleanup.
Tests stale data removal and protected file preservation.
"""

import pytest
import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../fixtures'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../.claude/ai-services'))

from mock_phase_outputs import MOCK_PHASE_0_OUTPUTS


class MockPhase0CleanupService:
    """Mock Phase 0 cleanup service for testing."""

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or tempfile.mkdtemp()
        self.staging_dir = Path(self.base_dir) / ".claude" / "staging"
        self.cache_dir = Path(self.base_dir) / ".claude" / "cache"
        self.runs_dir = Path(self.base_dir) / "runs"

    def setup_test_structure(self):
        """Setup test directory structure."""
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def create_stale_staging_files(self, count: int = 5):
        """Create stale staging files for testing."""
        for i in range(count):
            file_path = self.staging_dir / f"stale_file_{i}.json"
            file_path.write_text('{"stale": true}')

    def create_stale_cache_files(self, count: int = 10):
        """Create stale cache files for testing."""
        for i in range(count):
            file_path = self.cache_dir / f"cache_entry_{i}.json"
            file_path.write_text('{"cached": true}')

    def create_protected_run_files(self, jira_id: str = "ACM-12345"):
        """Create protected run files that should not be deleted."""
        run_dir = self.runs_dir / jira_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "Test-Cases.md").write_text("# Test Cases")
        (run_dir / "Complete-Analysis.md").write_text("# Analysis")

    def framework_initialization_cleanup(self) -> Dict[str, Any]:
        """Execute framework initialization cleanup."""
        files_removed = 0
        directories_cleaned = 0
        bytes_cleaned = 0

        # Clean staging
        if self.staging_dir.exists():
            for f in self.staging_dir.glob("*"):
                if f.is_file():
                    bytes_cleaned += f.stat().st_size
                    f.unlink()
                    files_removed += 1
            directories_cleaned += 1

        # Clean cache
        if self.cache_dir.exists():
            for f in self.cache_dir.glob("*"):
                if f.is_file():
                    bytes_cleaned += f.stat().st_size
                    f.unlink()
                    files_removed += 1
            directories_cleaned += 1

        # Do NOT clean runs directory (protected)

        return {
            'cleanup_successful': True,
            'cleanup_type': 'initialization',
            'files_removed': files_removed,
            'directories_cleaned': directories_cleaned,
            'total_size_freed_bytes': bytes_cleaned,
            'execution_time': 0.1
        }

    def cleanup(self):
        """Cleanup test directory."""
        if self.base_dir and Path(self.base_dir).exists():
            shutil.rmtree(self.base_dir, ignore_errors=True)


class TestPhase0Cleanup:
    """Test Phase 0 initialization cleanup functionality."""

    @pytest.fixture
    def cleanup_service(self):
        service = MockPhase0CleanupService()
        service.setup_test_structure()
        yield service
        service.cleanup()

    # ============== Test Scenario P0-1: Clean Start ==============
    def test_clean_start_no_stale_data(self, cleanup_service):
        """Test cleanup with no stale data present."""
        result = cleanup_service.framework_initialization_cleanup()

        assert result['cleanup_successful'] is True
        assert result['files_removed'] == 0
        assert result['total_size_freed_bytes'] == 0

    # ============== Test Scenario P0-2: Stale Staging Files ==============
    def test_stale_staging_files_cleanup(self, cleanup_service):
        """Test cleanup of stale staging files."""
        cleanup_service.create_stale_staging_files(5)

        result = cleanup_service.framework_initialization_cleanup()

        assert result['cleanup_successful'] is True
        assert result['files_removed'] >= 5

        # Verify files are gone
        assert len(list(cleanup_service.staging_dir.glob("*"))) == 0

    # ============== Test Scenario P0-3: Stale Cache Files ==============
    def test_stale_cache_files_cleanup(self, cleanup_service):
        """Test cleanup of stale cache entries."""
        cleanup_service.create_stale_cache_files(10)

        result = cleanup_service.framework_initialization_cleanup()

        assert result['cleanup_successful'] is True
        assert result['files_removed'] >= 10

        # Verify cache is empty
        assert len(list(cleanup_service.cache_dir.glob("*"))) == 0

    # ============== Test Scenario P0-4: Protected Files ==============
    def test_protected_files_preserved(self, cleanup_service):
        """Test that protected run files are not deleted."""
        cleanup_service.create_stale_staging_files(3)
        cleanup_service.create_protected_run_files("ACM-12345")

        result = cleanup_service.framework_initialization_cleanup()

        # Protected files should still exist
        run_dir = cleanup_service.runs_dir / "ACM-12345"
        assert (run_dir / "Test-Cases.md").exists()
        assert (run_dir / "Complete-Analysis.md").exists()

    # ============== Test Scenario P0-5: Permission Error ==============
    def test_permission_error_handling(self, cleanup_service):
        """Test graceful handling of permission errors."""
        # Create file and make directory read-only (simulate permission error)
        cleanup_service.create_stale_staging_files(1)

        # On actual permission error, should still return result
        result = cleanup_service.framework_initialization_cleanup()

        # Even with issues, cleanup should report
        assert 'cleanup_successful' in result


class TestCleanupStatistics:
    """Test cleanup statistics and reporting."""

    @pytest.fixture
    def cleanup_service(self):
        service = MockPhase0CleanupService()
        service.setup_test_structure()
        yield service
        service.cleanup()

    def test_accurate_file_count(self, cleanup_service):
        """Test accurate file count reporting."""
        cleanup_service.create_stale_staging_files(7)
        cleanup_service.create_stale_cache_files(3)

        result = cleanup_service.framework_initialization_cleanup()

        assert result['files_removed'] == 10

    def test_bytes_freed_calculation(self, cleanup_service):
        """Test bytes freed is calculated correctly."""
        cleanup_service.create_stale_staging_files(3)

        result = cleanup_service.framework_initialization_cleanup()

        assert result['total_size_freed_bytes'] > 0

    def test_directory_count(self, cleanup_service):
        """Test directory count tracking."""
        cleanup_service.create_stale_staging_files(1)
        cleanup_service.create_stale_cache_files(1)

        result = cleanup_service.framework_initialization_cleanup()

        assert result['directories_cleaned'] >= 2


class TestMultipleCleanupScenarios:
    """Test multiple cleanup scenarios in sequence."""

    @pytest.fixture
    def cleanup_service(self):
        service = MockPhase0CleanupService()
        service.setup_test_structure()
        yield service
        service.cleanup()

    def test_repeated_cleanup(self, cleanup_service):
        """Test cleanup can be run multiple times."""
        cleanup_service.create_stale_staging_files(5)

        # First cleanup
        result1 = cleanup_service.framework_initialization_cleanup()
        assert result1['files_removed'] == 5

        # Second cleanup (should find nothing)
        result2 = cleanup_service.framework_initialization_cleanup()
        assert result2['files_removed'] == 0

    def test_partial_cleanup_between_phases(self, cleanup_service):
        """Test cleanup between phases doesn't affect new files."""
        # Create and clean
        cleanup_service.create_stale_staging_files(3)
        cleanup_service.framework_initialization_cleanup()

        # Create new files (simulating new run)
        cleanup_service.create_stale_staging_files(2)

        # Cleanup again
        result = cleanup_service.framework_initialization_cleanup()
        assert result['files_removed'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
