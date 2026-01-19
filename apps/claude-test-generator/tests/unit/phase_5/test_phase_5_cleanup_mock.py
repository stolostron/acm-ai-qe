"""
Phase 5 Comprehensive Cleanup Mock Tests
=========================================

Comprehensive mock-based tests for Phase 5 final cleanup functionality.
Tests temporary file removal and essential file preservation.
"""

import pytest
import asyncio
import sys
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../fixtures'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../.claude/ai-services'))

from mock_phase_outputs import MOCK_PHASE_5_OUTPUTS


class MockPhase5CleanupService:
    """Mock Phase 5 cleanup service for testing."""

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or tempfile.mkdtemp()
        self.essential_files = ['Test-Cases.md', 'Complete-Analysis.md']
        self.temp_patterns = ['*.tmp', '*_staging.json', '*_qe_intelligence.json',
                             '*_phase_3_input.json', '*_agent_*.json']

    def setup_run_directory(self, run_id: str = "ACM-12345-20250117-120000"):
        """Setup a mock run directory with temp and essential files."""
        run_dir = Path(self.base_dir) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create essential files
        (run_dir / "Test-Cases.md").write_text("# Test Cases\n## TC-001...")
        (run_dir / "Complete-Analysis.md").write_text("# Complete Analysis...")

        # Create temporary files
        (run_dir / "staging_data.tmp").write_text('{"temp": true}')
        (run_dir / "agent_intelligence_staging.json").write_text('{}')
        (run_dir / "qe_intelligence.json").write_text('{}')
        (run_dir / "phase_3_input.json").write_text('{}')
        (run_dir / "agent_a_output.json").write_text('{}')
        (run_dir / "agent_b_output.json").write_text('{}')

        return run_dir

    def execute_comprehensive_cleanup(self, run_dir: str) -> Dict[str, Any]:
        """Execute comprehensive cleanup for run directory."""
        run_path = Path(run_dir)

        if not run_path.exists():
            return {
                'success': False,
                'cleanup_statistics': {'files_removed': 0, 'directories_removed': 0, 'bytes_cleaned': 0},
                'error': 'Run directory not found'
            }

        files_removed = 0
        bytes_cleaned = 0

        # Get all files
        all_files = list(run_path.glob("*"))

        for file_path in all_files:
            if file_path.is_file() and file_path.name not in self.essential_files:
                # Check if it's a temp file
                is_temp = any(
                    file_path.match(pattern) for pattern in self.temp_patterns
                ) or file_path.suffix in ['.tmp', '.temp']

                # Also remove agent output files and staging files
                is_temp = is_temp or 'staging' in file_path.name.lower()
                is_temp = is_temp or 'agent_' in file_path.name.lower()
                is_temp = is_temp or 'phase_' in file_path.name.lower()
                is_temp = is_temp or 'intelligence' in file_path.name.lower()

                if is_temp:
                    bytes_cleaned += file_path.stat().st_size
                    file_path.unlink()
                    files_removed += 1

        # Verify essential files
        preserved_files = []
        for essential in self.essential_files:
            if (run_path / essential).exists():
                preserved_files.append(essential)

        return {
            'success': True,
            'cleanup_statistics': {
                'files_removed': files_removed,
                'directories_removed': 0,
                'bytes_cleaned': bytes_cleaned
            },
            'essential_files_validation': {
                'preserved_files': preserved_files,
                'validation_passed': len(preserved_files) == len(self.essential_files)
            },
            'summary': f'Cleanup completed: {files_removed} files removed',
            'execution_time': 0.1
        }

    def cleanup(self):
        """Cleanup test directory."""
        if self.base_dir and Path(self.base_dir).exists():
            shutil.rmtree(self.base_dir, ignore_errors=True)


class TestPhase5Cleanup:
    """Test Phase 5 comprehensive cleanup functionality."""

    @pytest.fixture
    def cleanup_service(self):
        service = MockPhase5CleanupService()
        yield service
        service.cleanup()

    # ============== Test Scenario P5-1: Normal Cleanup ==============
    def test_normal_cleanup(self, cleanup_service):
        """Test normal cleanup removes temp files."""
        run_dir = cleanup_service.setup_run_directory()

        result = cleanup_service.execute_comprehensive_cleanup(str(run_dir))

        assert result['success'] is True
        assert result['cleanup_statistics']['files_removed'] >= 4

    # ============== Test Scenario P5-2: Protected Files ==============
    def test_protected_files_preserved(self, cleanup_service):
        """Test essential files are preserved."""
        run_dir = cleanup_service.setup_run_directory()

        result = cleanup_service.execute_comprehensive_cleanup(str(run_dir))

        # Essential files should still exist
        assert (run_dir / "Test-Cases.md").exists()
        assert (run_dir / "Complete-Analysis.md").exists()

        # Validation should pass
        assert result['essential_files_validation']['validation_passed'] is True
        assert 'Test-Cases.md' in result['essential_files_validation']['preserved_files']
        assert 'Complete-Analysis.md' in result['essential_files_validation']['preserved_files']

    # ============== Test Scenario P5-3: Empty Run Directory ==============
    def test_empty_run_directory(self, cleanup_service):
        """Test cleanup of empty directory."""
        run_dir = Path(cleanup_service.base_dir) / "empty_run"
        run_dir.mkdir(parents=True, exist_ok=True)

        result = cleanup_service.execute_comprehensive_cleanup(str(run_dir))

        assert result['success'] is True
        assert result['cleanup_statistics']['files_removed'] == 0

    # ============== Test Scenario P5-4: Directory Not Found ==============
    def test_nonexistent_directory(self, cleanup_service):
        """Test handling of nonexistent directory."""
        result = cleanup_service.execute_comprehensive_cleanup("/nonexistent/path")

        assert result['success'] is False
        assert 'error' in result

    # ============== Test Scenario P5-5: Final Output Structure ==============
    def test_final_output_structure(self, cleanup_service):
        """Test only essential files remain after cleanup."""
        run_dir = cleanup_service.setup_run_directory()

        cleanup_service.execute_comprehensive_cleanup(str(run_dir))

        # List remaining files
        remaining_files = [f.name for f in run_dir.glob("*") if f.is_file()]

        # Should only have essential files
        assert set(remaining_files) == set(cleanup_service.essential_files)


class TestCleanupStatistics:
    """Test cleanup statistics and reporting."""

    @pytest.fixture
    def cleanup_service(self):
        service = MockPhase5CleanupService()
        yield service
        service.cleanup()

    def test_accurate_file_count(self, cleanup_service):
        """Test accurate file count in cleanup statistics."""
        run_dir = cleanup_service.setup_run_directory()

        result = cleanup_service.execute_comprehensive_cleanup(str(run_dir))

        # Should have removed temp files, kept essential
        assert result['cleanup_statistics']['files_removed'] >= 4

    def test_bytes_calculation(self, cleanup_service):
        """Test bytes cleaned calculation."""
        run_dir = cleanup_service.setup_run_directory()

        result = cleanup_service.execute_comprehensive_cleanup(str(run_dir))

        assert result['cleanup_statistics']['bytes_cleaned'] > 0


class TestEssentialFileValidation:
    """Test essential file validation."""

    @pytest.fixture
    def cleanup_service(self):
        service = MockPhase5CleanupService()
        yield service
        service.cleanup()

    def test_all_essential_files_present(self, cleanup_service):
        """Test validation when all essential files are present."""
        run_dir = cleanup_service.setup_run_directory()

        result = cleanup_service.execute_comprehensive_cleanup(str(run_dir))

        assert result['essential_files_validation']['validation_passed'] is True
        assert len(result['essential_files_validation']['preserved_files']) == 2

    def test_missing_essential_file(self, cleanup_service):
        """Test validation when essential file is missing."""
        run_dir = cleanup_service.setup_run_directory()

        # Remove one essential file before cleanup
        (run_dir / "Complete-Analysis.md").unlink()

        result = cleanup_service.execute_comprehensive_cleanup(str(run_dir))

        # Should report missing file
        assert len(result['essential_files_validation']['preserved_files']) == 1
        assert 'Test-Cases.md' in result['essential_files_validation']['preserved_files']


class TestCleanupPatterns:
    """Test temp file pattern matching."""

    @pytest.fixture
    def cleanup_service(self):
        service = MockPhase5CleanupService()
        yield service
        service.cleanup()

    def test_staging_file_removal(self, cleanup_service):
        """Test staging files are removed."""
        run_dir = cleanup_service.setup_run_directory()

        # Add more staging files
        (run_dir / "test_staging.json").write_text('{}')
        (run_dir / "data_staging.json").write_text('{}')

        result = cleanup_service.execute_comprehensive_cleanup(str(run_dir))

        # Staging files should be gone
        assert not (run_dir / "test_staging.json").exists()
        assert not (run_dir / "data_staging.json").exists()

    def test_agent_output_removal(self, cleanup_service):
        """Test agent output files are removed."""
        run_dir = cleanup_service.setup_run_directory()

        result = cleanup_service.execute_comprehensive_cleanup(str(run_dir))

        # Agent files should be gone
        assert not (run_dir / "agent_a_output.json").exists()
        assert not (run_dir / "agent_b_output.json").exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
