"""
Drift detection tests for the ACM Hub Health Diagnostician.

Ensures consistency across CLAUDE.md, docs/, knowledge/, and slash commands.
These tests scan source files with regex -- they don't execute diagnostics
or require cluster access. Total runtime: < 0.5 seconds.

Test classes:
  1. TestKnowledgeReferenceIntegrity -- every file path referenced in
     CLAUDE.md and docs must exist on disk
  2. TestCountConsistency -- diagnostic layers (12), dependency chains (11),
     traps (13), phases (6), issue fields (9), diagnostics files (8)
  3. TestReportFormatConsistency -- issue template fields and verdict rules
     must match between CLAUDE.md and docs/05-OUTPUT-AND-REPORTING.md
  4. TestSlashCommandIntegrity -- command files must reference valid phases
     and match the methodology in CLAUDE.md
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.regression

APP_ROOT = Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# Class 1: Knowledge Reference Integrity
# ---------------------------------------------------------------------------

class TestKnowledgeReferenceIntegrity:
    """Every knowledge/ and docs/ file path referenced in CLAUDE.md and docs
    must exist on disk. Catches stale references when files are renamed,
    moved, or deleted."""

    KNOWLEDGE_PATH_RE = re.compile(
        r'(?:knowledge/[a-zA-Z0-9_./-]+\.(?:md|yaml))'
    )
    DOCS_PATH_RE = re.compile(
        r'(?:docs/[a-zA-Z0-9_./-]+\.(?:md|html))'
    )

    # Paths that appear as examples or patterns, not actual file references
    ALLOWED_MISSING = {
        'knowledge/learned/',  # Directory reference, not a file
    }

    def _extract_file_refs(self, filepath, pattern):
        """Extract all file path references from a file using the given regex."""
        text = filepath.read_text()
        return set(pattern.findall(text))

    def test_claude_md_knowledge_references(self):
        """Every knowledge/ path in CLAUDE.md must exist on disk."""
        claude_md = APP_ROOT / 'CLAUDE.md'
        refs = self._extract_file_refs(claude_md, self.KNOWLEDGE_PATH_RE)
        missing = []
        for ref in sorted(refs):
            if any(ref.startswith(a) for a in self.ALLOWED_MISSING):
                continue
            if not (APP_ROOT / ref).exists():
                missing.append(ref)
        assert not missing, (
            f"CLAUDE.md references {len(missing)} knowledge file(s) that "
            f"don't exist:\n" + '\n'.join(f"  - {m}" for m in missing)
        )

    def test_claude_md_docs_references(self):
        """Every docs/ path in CLAUDE.md must exist on disk."""
        claude_md = APP_ROOT / 'CLAUDE.md'
        refs = self._extract_file_refs(claude_md, self.DOCS_PATH_RE)
        missing = []
        for ref in sorted(refs):
            if not (APP_ROOT / ref).exists():
                missing.append(ref)
        assert not missing, (
            f"CLAUDE.md references {len(missing)} docs file(s) that "
            f"don't exist:\n" + '\n'.join(f"  - {m}" for m in missing)
        )

    def test_docs_knowledge_references(self):
        """Every knowledge/ path in docs/*.md must exist on disk."""
        docs_dir = APP_ROOT / 'docs'
        if not docs_dir.exists():
            pytest.skip("docs/ directory not found")
        missing = []
        for doc_file in sorted(docs_dir.glob('*.md')):
            refs = self._extract_file_refs(doc_file, self.KNOWLEDGE_PATH_RE)
            for ref in sorted(refs):
                if any(ref.startswith(a) for a in self.ALLOWED_MISSING):
                    continue
                if not (APP_ROOT / ref).exists():
                    missing.append(f"{doc_file.name}: {ref}")
        assert not missing, (
            f"Docs reference {len(missing)} knowledge file(s) that don't "
            f"exist:\n" + '\n'.join(f"  - {m}" for m in missing)
        )

    def test_knowledge_readme_diagnostics_count(self):
        """knowledge/README.md diagnostics file count must match actual files
        on disk."""
        readme = APP_ROOT / 'knowledge' / 'README.md'
        text = readme.read_text()
        match = re.search(r'Investigation Methodology \((\d+) files\)', text)
        assert match, "Could not find diagnostics file count in README.md"
        documented_count = int(match.group(1))
        actual_count = len(list(
            (APP_ROOT / 'knowledge' / 'diagnostics').glob('*.md')
        ))
        assert documented_count == actual_count, (
            f"README.md says {documented_count} diagnostics files but "
            f"{actual_count} exist on disk"
        )


# ---------------------------------------------------------------------------
# Class 2: Count Consistency
# ---------------------------------------------------------------------------

class TestCountConsistency:
    """Numeric constants that appear in multiple files must agree.
    Each test defines the expected value and checks all locations."""

    EXPECTED_LAYER_COUNT = 12
    EXPECTED_CHAIN_COUNT = 12
    EXPECTED_TRAP_COUNT = 14
    EXPECTED_PHASE_COUNT = 6
    EXPECTED_ISSUE_FIELDS = 9
    EXPECTED_DIAGNOSTICS_FILES = 8

    def test_layer_count_in_claude_md(self):
        """CLAUDE.md must reference the correct layer count."""
        text = (APP_ROOT / 'CLAUDE.md').read_text()
        match = re.search(r'(\d+)-layer', text)
        assert match, "No layer count found in CLAUDE.md"
        assert int(match.group(1)) == self.EXPECTED_LAYER_COUNT, (
            f"CLAUDE.md says {match.group(1)}-layer but expected "
            f"{self.EXPECTED_LAYER_COUNT}"
        )

    def test_layer_count_in_diagnostic_layers(self):
        """diagnostic-layers.md must define exactly N layers."""
        text = (APP_ROOT / 'knowledge' / 'diagnostics' /
                'diagnostic-layers.md').read_text()
        layers = re.findall(r'^### Layer \d+:', text, re.MULTILINE)
        assert len(layers) == self.EXPECTED_LAYER_COUNT, (
            f"diagnostic-layers.md defines {len(layers)} layers but expected "
            f"{self.EXPECTED_LAYER_COUNT}"
        )

    def test_chain_count_in_claude_md(self):
        """CLAUDE.md must reference the correct dependency chain count."""
        text = (APP_ROOT / 'CLAUDE.md').read_text()
        match = re.search(r'(\d+)\s+chains?\)', text)
        if not match:
            match = re.search(r'(\d+)\s+critical cascade', text, re.IGNORECASE)
        if not match:
            match = re.search(r'\((\d+)\s+chains', text)
        assert match, "No chain count found in CLAUDE.md"
        assert int(match.group(1)) == self.EXPECTED_CHAIN_COUNT, (
            f"CLAUDE.md says {match.group(1)} chains but expected "
            f"{self.EXPECTED_CHAIN_COUNT}"
        )

    def test_chain_count_in_dependency_chains(self):
        """dependency-chains.md must define exactly N chains."""
        text = (APP_ROOT / 'knowledge' / 'diagnostics' /
                'dependency-chains.md').read_text()
        chains = re.findall(r'^## Chain \d+:', text, re.MULTILINE)
        assert len(chains) == self.EXPECTED_CHAIN_COUNT, (
            f"dependency-chains.md defines {len(chains)} chains but expected "
            f"{self.EXPECTED_CHAIN_COUNT}"
        )

    def test_trap_count_in_claude_md(self):
        """CLAUDE.md must reference the correct diagnostic trap count."""
        text = (APP_ROOT / 'CLAUDE.md').read_text()
        match = re.search(r'(\d+) traps', text)
        assert match, "No trap count found in CLAUDE.md"
        assert int(match.group(1)) == self.EXPECTED_TRAP_COUNT, (
            f"CLAUDE.md says {match.group(1)} traps but expected "
            f"{self.EXPECTED_TRAP_COUNT}"
        )

    def test_trap_count_in_common_traps(self):
        """common-diagnostic-traps.md must define exactly N traps."""
        text = (APP_ROOT / 'knowledge' / 'diagnostics' /
                'common-diagnostic-traps.md').read_text()
        traps = re.findall(r'^## Trap \d+:', text, re.MULTILINE)
        assert len(traps) == self.EXPECTED_TRAP_COUNT, (
            f"common-diagnostic-traps.md defines {len(traps)} traps but "
            f"expected {self.EXPECTED_TRAP_COUNT}"
        )

    def test_phase_count_in_claude_md(self):
        """CLAUDE.md must define exactly N phases."""
        text = (APP_ROOT / 'CLAUDE.md').read_text()
        phases = re.findall(r'^### Phase \d+:', text, re.MULTILINE)
        assert len(phases) == self.EXPECTED_PHASE_COUNT, (
            f"CLAUDE.md defines {len(phases)} phases but expected "
            f"{self.EXPECTED_PHASE_COUNT}"
        )

    def test_issue_field_count_in_claude_md(self):
        """CLAUDE.md issue template must have exactly N fields."""
        text = (APP_ROOT / 'CLAUDE.md').read_text()
        match = re.search(r'All (\w+) issue fields are required', text)
        assert match, "No issue field count found in CLAUDE.md"
        word_to_num = {
            'nine': 9, 'eight': 8, 'seven': 7, 'six': 6,
            'ten': 10, 'eleven': 11, 'twelve': 12,
        }
        count = word_to_num.get(match.group(1).lower())
        if count is None:
            count = int(match.group(1))
        assert count == self.EXPECTED_ISSUE_FIELDS, (
            f"CLAUDE.md says {count} issue fields but expected "
            f"{self.EXPECTED_ISSUE_FIELDS}"
        )

    def test_diagnostics_file_count(self):
        """Actual diagnostics files on disk must match expected count."""
        actual = len(list(
            (APP_ROOT / 'knowledge' / 'diagnostics').glob('*.md')
        ))
        assert actual == self.EXPECTED_DIAGNOSTICS_FILES, (
            f"Expected {self.EXPECTED_DIAGNOSTICS_FILES} diagnostics files "
            f"but found {actual}"
        )


# ---------------------------------------------------------------------------
# Class 3: Report Format Consistency
# ---------------------------------------------------------------------------

class TestReportFormatConsistency:
    """The issue detail template and verdict derivation rules must match
    between CLAUDE.md and docs/05-OUTPUT-AND-REPORTING.md."""

    EXPECTED_ISSUE_FIELDS = {
        'What', 'Evidence', 'Root Cause', 'Layer', 'Known Issue',
        'Fix Version', 'Cluster-Fixable', 'Impact', 'Recommended Action',
    }

    EXPECTED_VERDICTS = {'HEALTHY', 'DEGRADED', 'CRITICAL'}

    FIELD_RE = re.compile(r'\*\*(\w[\w\s-]+?)\*\*:')

    def _extract_issue_fields(self, text, start_marker):
        """Extract issue field names from a template section.
        Stops at the next ## heading or blank line after fields end."""
        start = text.find(start_marker)
        if start == -1:
            return set()
        lines = text[start:].split('\n')[1:]  # skip the marker line
        fields = set()
        for line in lines:
            stripped = line.strip()
            # Stop at next section heading or end of field block
            if stripped.startswith('##') or stripped.startswith('```'):
                break
            match = self.FIELD_RE.search(line)
            if match and stripped.startswith('- **'):
                fields.add(match.group(1))
        return fields

    def test_claude_md_issue_fields(self):
        """CLAUDE.md issue template must contain all expected fields."""
        text = (APP_ROOT / 'CLAUDE.md').read_text()
        fields = self._extract_issue_fields(text, '### [SEVERITY]')
        missing = self.EXPECTED_ISSUE_FIELDS - fields
        extra = fields - self.EXPECTED_ISSUE_FIELDS
        assert not missing, f"CLAUDE.md template missing fields: {missing}"
        assert not extra, f"CLAUDE.md template has unexpected fields: {extra}"

    def test_docs_issue_fields(self):
        """docs/05-OUTPUT-AND-REPORTING.md issue template must contain all
        expected fields."""
        docs_file = APP_ROOT / 'docs' / '05-OUTPUT-AND-REPORTING.md'
        if not docs_file.exists():
            pytest.skip("docs/05-OUTPUT-AND-REPORTING.md not found")
        text = docs_file.read_text()
        fields = self._extract_issue_fields(text, '### [SEVERITY]')
        missing = self.EXPECTED_ISSUE_FIELDS - fields
        extra = fields - self.EXPECTED_ISSUE_FIELDS
        assert not missing, f"Docs template missing fields: {missing}"
        assert not extra, f"Docs template has unexpected fields: {extra}"

    def test_verdict_rules_in_claude_md(self):
        """CLAUDE.md must contain all three verdict derivation rules."""
        text = (APP_ROOT / 'CLAUDE.md').read_text()
        for verdict in self.EXPECTED_VERDICTS:
            assert f'`{verdict}`' in text, (
                f"CLAUDE.md missing verdict value: {verdict}"
            )
        assert 'Any component WARN, no CRIT' in text, (
            "CLAUDE.md missing DEGRADED derivation rule"
        )

    def test_verdict_rules_in_docs(self):
        """docs/05-OUTPUT-AND-REPORTING.md must contain all three verdict
        derivation rules."""
        docs_file = APP_ROOT / 'docs' / '05-OUTPUT-AND-REPORTING.md'
        if not docs_file.exists():
            pytest.skip("docs/05-OUTPUT-AND-REPORTING.md not found")
        text = docs_file.read_text()
        assert 'Any WARN, no CRIT' in text, (
            "Docs missing DEGRADED derivation rule"
        )
        assert 'HEALTHY' in text and 'DEGRADED' in text and 'CRITICAL' in text


# ---------------------------------------------------------------------------
# Class 4: Slash Command Integrity
# ---------------------------------------------------------------------------

class TestSlashCommandIntegrity:
    """Slash command files in .claude/commands/ must reference valid phase
    numbers and be consistent with the methodology in CLAUDE.md."""

    EXPECTED_PHASE_COUNT = 6

    def test_deep_command_references_all_phases(self):
        """The /deep command must reference all 6 phases."""
        cmd_file = APP_ROOT / '.claude' / 'commands' / 'deep.md'
        if not cmd_file.exists():
            pytest.skip("deep.md command not found")
        text = cmd_file.read_text()
        match = re.search(r'all (\d+) phases', text)
        assert match, "/deep command doesn't mention phase count"
        assert int(match.group(1)) == self.EXPECTED_PHASE_COUNT, (
            f"/deep says {match.group(1)} phases but expected "
            f"{self.EXPECTED_PHASE_COUNT}"
        )

    def test_health_check_command_references_phases_1_4(self):
        """The /health-check command must reference Phases 1-4."""
        cmd_file = APP_ROOT / '.claude' / 'commands' / 'health-check.md'
        if not cmd_file.exists():
            pytest.skip("health-check.md command not found")
        text = cmd_file.read_text()
        assert 'Phases 1-4' in text or 'Phase 1' in text, (
            "/health-check command doesn't reference Phases 1-4"
        )

    def test_sanity_command_references_phase_1(self):
        """The /sanity command must reference Phase 1."""
        cmd_file = APP_ROOT / '.claude' / 'commands' / 'sanity.md'
        if not cmd_file.exists():
            pytest.skip("sanity.md command not found")
        text = cmd_file.read_text()
        assert 'Phase 1' in text, (
            "/sanity command doesn't reference Phase 1"
        )

    def test_investigate_command_references_all_phases(self):
        """The /investigate command must reference all 6 phases."""
        cmd_file = APP_ROOT / '.claude' / 'commands' / 'investigate.md'
        if not cmd_file.exists():
            pytest.skip("investigate.md command not found")
        text = cmd_file.read_text()
        match = re.search(r'all (\d+) phases', text)
        assert match, "/investigate command doesn't mention phase count"
        assert int(match.group(1)) == self.EXPECTED_PHASE_COUNT, (
            f"/investigate says {match.group(1)} phases but expected "
            f"{self.EXPECTED_PHASE_COUNT}"
        )

    def test_commands_reference_methodology(self):
        """All command files should reference the diagnostic methodology."""
        cmd_dir = APP_ROOT / '.claude' / 'commands'
        if not cmd_dir.exists():
            pytest.skip(".claude/commands/ directory not found")
        # Commands must reference at least one methodology indicator
        methodology_indicators = [
            'CLAUDE.md', 'methodology', 'phase', 'knowledge',
        ]
        for cmd_file in sorted(cmd_dir.glob('*.md')):
            text = cmd_file.read_text().lower()
            found = any(ind.lower() in text for ind in methodology_indicators)
            assert found, (
                f"{cmd_file.name} doesn't reference any methodology "
                f"indicator: {methodology_indicators}"
            )
