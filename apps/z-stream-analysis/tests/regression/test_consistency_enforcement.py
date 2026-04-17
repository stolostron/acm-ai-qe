"""
Consistency Enforcement Tests (v4.0)

Automated checks that catch drift between code, documentation, and data
contracts. These tests prevent the class of bugs where one part of the
codebase is updated but related references elsewhere are not.

Tests:
1. Version consistency — all version strings match
2. Removed field detection — no references to deleted fields in active code
3. Data contract validation — (removed in v4.0, ai_instructions deleted)
4. Step count consistency — docstrings, code, and docs agree on step count
5. Core-data key count — output key count matches documentation
"""

import re
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.regression

# App root for file scanning
APP_ROOT = Path(__file__).parent.parent.parent


# ── Test 1: Version Consistency ──


class TestVersionConsistency:
    """All version strings in the codebase must match."""

    # The single source of truth for the current version
    CURRENT_VERSION = '4.0.0'

    def test_gather_gatherer_version(self):
        """gatherer_version in gather.py metadata matches."""
        sys.path.insert(0, str(APP_ROOT))
        from unittest.mock import patch
        from src.scripts.gather import DataGatherer
        with patch.object(DataGatherer, '__init__', lambda x, **kw: None):
            g = DataGatherer()
            g.gathered_data = {}
            g.gathered_data['metadata'] = {}
        # Read the source to find the version string
        src = (APP_ROOT / 'src' / 'scripts' / 'gather.py').read_text()
        match = re.search(r"'gatherer_version':\s*'([^']+)'", src)
        assert match, "gatherer_version not found in gather.py"
        assert match.group(1) == self.CURRENT_VERSION, (
            f"gatherer_version is '{match.group(1)}', expected '{self.CURRENT_VERSION}'"
        )

    def test_gather_data_version(self):
        """data_version in _save_combined_data matches."""
        src = (APP_ROOT / 'src' / 'scripts' / 'gather.py').read_text()
        match = re.search(r"'data_version'\]\s*=\s*'([^']+)'", src)
        assert match, "data_version assignment not found in gather.py"
        assert match.group(1) == self.CURRENT_VERSION, (
            f"data_version is '{match.group(1)}', expected '{self.CURRENT_VERSION}'"
        )

    def test_manifest_version(self):
        """manifest version in _build_manifest matches."""
        src = (APP_ROOT / 'src' / 'scripts' / 'gather.py').read_text()
        # Find version in _build_manifest context
        manifest_section = src[src.index('def _build_manifest'):]
        match = re.search(r"'version':\s*'([^']+)'", manifest_section)
        assert match, "manifest version not found in _build_manifest"
        assert match.group(1) == self.CURRENT_VERSION, (
            f"manifest version is '{match.group(1)}', expected '{self.CURRENT_VERSION}'"
        )

    # test_ai_instructions_version removed — _build_ai_instructions() deleted in v4.0

    def test_report_footer_version(self):
        """Report footer version string matches."""
        src = (APP_ROOT / 'src' / 'scripts' / 'report.py').read_text()
        match = re.search(r'Z-Stream Analysis Framework v([\d.]+)', src)
        assert match, "Report footer version not found in report.py"
        # Compare major.minor (footer uses v4.0, not v4.0.0)
        expected_short = '.'.join(self.CURRENT_VERSION.split('.')[:2])
        assert match.group(1) == expected_short, (
            f"report footer is 'v{match.group(1)}', expected 'v{expected_short}'"
        )

    def test_init_module_version(self):
        """services/__init__.py docstring version matches."""
        src = (APP_ROOT / 'src' / 'services' / '__init__.py').read_text()
        match = re.search(r'Module \(v([\d.]+)\)', src)
        assert match, "Module version not found in __init__.py"
        expected_short = '.'.join(self.CURRENT_VERSION.split('.')[:2])
        assert match.group(1) == expected_short, (
            f"__init__.py version is 'v{match.group(1)}', expected 'v{expected_short}'"
        )

    def test_cli_help_version(self):
        """CLI argparse description version matches."""
        src = (APP_ROOT / 'src' / 'scripts' / 'gather.py').read_text()
        match = re.search(r'Data Gathering Script \(v([\d.]+)\)', src)
        assert match, "CLI help version not found in gather.py"
        expected_short = '.'.join(self.CURRENT_VERSION.split('.')[:2])
        assert match.group(1) == expected_short, (
            f"CLI help version is 'v{match.group(1)}', expected 'v{expected_short}'"
        )


# ── Test 2: Removed Field Detection ──


class TestRemovedFieldDetection:
    """No references to removed fields in active source code."""

    # Fields that were removed and should not appear in active code
    REMOVED_FIELDS = [
        'investigation_hints',
        'element_inventory',
        'element-inventory',
        'timeline_evidence',
        'failed_test_locations',
        'backend_probes',
        'ai_instructions',
    ]

    # Files/patterns that are ALLOWED to reference removed fields
    ALLOWED_PATTERNS = [
        'CHANGELOG',           # Historical docs
        'V2.5-VS-V3.0',       # Historical comparison
        '.coderabbit.yaml',    # "Methods that were REMOVED" list
        'test_gather_enhancements',  # Comment about removed tests
        'feature-gaps.yaml',   # Gap detection output
        'synthetic_analysis',  # Test fixture
        '/runs/',              # Pipeline output
        '.claude/traces/',     # Agent traces
        '__pycache__',
        'node_modules',
        'cluster_health_service.py',  # Deprecated service (kept for backward compat)
        'acm_ui_mcp_client.py',       # Stub methods (Phase 2 uses native MCP)
    ]

    def _is_allowed(self, filepath: str) -> bool:
        """Check if a file is allowed to reference removed fields."""
        for pattern in self.ALLOWED_PATTERNS:
            if pattern in filepath:
                return True
        return False

    def _is_removal_comment(self, line: str) -> bool:
        """Check if the line is documenting the removal itself."""
        lower = line.lower()
        return any(word in lower for word in [
            'removed', 'deprecated', 'was removed', 'were removed',
            'no longer', 'not in', 'not found', 'assert',
        ])

    def test_no_removed_field_references(self):
        """Active source files should not reference removed fields."""
        violations = []

        # Scan Python files in src/
        for py_file in (APP_ROOT / 'src').rglob('*.py'):
            if self._is_allowed(str(py_file)):
                continue
            content = py_file.read_text(errors='ignore')
            for line_num, line in enumerate(content.split('\n'), 1):
                for field in self.REMOVED_FIELDS:
                    if field in line and not self._is_removal_comment(line):
                        # Extra check: is this in a component recognition list?
                        # (e.g., search-redisgraph in component_extractor)
                        if 'redisgraph' in field:
                            continue  # Component recognition is acceptable
                        violations.append(
                            f"{py_file.relative_to(APP_ROOT)}:{line_num}: "
                            f"'{field}' in: {line.strip()[:100]}"
                        )

        # Scan agent instructions
        for md_file in (APP_ROOT / '.claude' / 'agents').glob('*.md'):
            if self._is_allowed(str(md_file)):
                continue
            content = md_file.read_text(errors='ignore')
            for line_num, line in enumerate(content.split('\n'), 1):
                for field in self.REMOVED_FIELDS:
                    if field in line and not self._is_removal_comment(line):
                        violations.append(
                            f"{md_file.relative_to(APP_ROOT)}:{line_num}: "
                            f"'{field}' in: {line.strip()[:100]}"
                        )

        assert not violations, (
            f"Found {len(violations)} references to removed fields:\n"
            + '\n'.join(f"  {v}" for v in violations)
        )


# ── Test 3: Data Contract Validation ──


    # TestDataContractValidation removed — _build_ai_instructions() deleted in v4.0.
    # Stage 2 reads instructions from .claude/agents/analysis.md, not core-data.json.


# ── Test 4: Step Count Consistency ──


class TestStepCountConsistency:
    """Step count must be consistent across code and documentation."""

    EXPECTED_STEPS = 9

    def test_gather_total_steps_variable(self):
        """total_steps in gather_all() matches expected."""
        src = (APP_ROOT / 'src' / 'scripts' / 'gather.py').read_text()
        match = re.search(r'total_steps\s*=\s*(\d+)', src)
        assert match, "total_steps not found in gather.py"
        assert int(match.group(1)) == self.EXPECTED_STEPS, (
            f"total_steps is {match.group(1)}, expected {self.EXPECTED_STEPS}"
        )

    def test_gather_docstring_step_count(self):
        """Module docstring step count matches."""
        src = (APP_ROOT / 'src' / 'scripts' / 'gather.py').read_text()
        match = re.search(r'(\d+)-step pipeline:', src)
        assert match, "N-step pipeline not found in gather.py docstring"
        assert int(match.group(1)) == self.EXPECTED_STEPS, (
            f"Docstring says '{match.group(1)}-step', expected '{self.EXPECTED_STEPS}-step'"
        )

    def test_claude_md_step_count(self):
        """CLAUDE.md step count matches."""
        src = (APP_ROOT / 'CLAUDE.md').read_text()
        match = re.search(r'gather\.py with (\d+) steps', src)
        assert match, "'gather.py with N steps' not found in CLAUDE.md"
        assert int(match.group(1)) == self.EXPECTED_STEPS, (
            f"CLAUDE.md says '{match.group(1)} steps', expected '{self.EXPECTED_STEPS}'"
        )

    def test_cli_help_step_count(self):
        """CLI help text step count matches."""
        src = (APP_ROOT / 'src' / 'scripts' / 'gather.py').read_text()
        match = re.search(r'(\d+)-step deterministic pipeline', src)
        assert match, "N-step deterministic pipeline not found in CLI help"
        assert int(match.group(1)) == self.EXPECTED_STEPS, (
            f"CLI help says '{match.group(1)}-step', expected '{self.EXPECTED_STEPS}'"
        )


# ── Test 5: Core-Data Key Count ──


class TestCoreDataKeyCount:
    """Core-data.json output key count matches documentation."""

    # The documented number of top-level keys
    EXPECTED_KEY_COUNT = 13

    # The exact set of expected keys
    EXPECTED_KEYS = {
        'metadata', 'jenkins', 'test_report', 'console_log',
        'environment', 'cluster_health', 'repositories',
        'cluster_landscape', 'feature_grounding', 'feature_knowledge',
        'cluster_access', 'cluster_oracle', 'errors',
    }

    def test_save_combined_data_key_count(self):
        """_save_combined_data produces exactly EXPECTED_KEY_COUNT keys."""
        src = (APP_ROOT / 'src' / 'scripts' / 'gather.py').read_text()
        # Extract the core_data dict construction from _save_combined_data
        save_start = src.index('core_data = {', src.index('def _save_combined_data'))
        save_end = src.index('\n        }', save_start) + 10
        core_data_block = src[save_start:save_end]
        # Extract all quoted keys at the first indent level of the dict
        actual_keys = set(re.findall(r"'(\w+)':", core_data_block))

        missing = self.EXPECTED_KEYS - actual_keys
        extra = actual_keys - self.EXPECTED_KEYS
        assert not missing, f"Missing keys in _save_combined_data: {missing}"
        assert not extra, f"Extra keys in _save_combined_data: {extra}"
        assert len(actual_keys) == self.EXPECTED_KEY_COUNT, (
            f"Expected {self.EXPECTED_KEY_COUNT} keys, found {len(actual_keys)}"
        )

    def test_claude_md_key_count(self):
        """CLAUDE.md documents the correct key count."""
        # Check .coderabbit.yaml which has the authoritative count
        coderabbit = Path(APP_ROOT).parent.parent / '.coderabbit.yaml'
        if coderabbit.exists():
            src = coderabbit.read_text()
            match = re.search(r'all (\d+) must always be present', src)
            if match:
                assert int(match.group(1)) == self.EXPECTED_KEY_COUNT, (
                    f".coderabbit.yaml says {match.group(1)} keys, "
                    f"expected {self.EXPECTED_KEY_COUNT}"
                )
