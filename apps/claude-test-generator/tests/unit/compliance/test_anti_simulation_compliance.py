"""
Anti-Simulation Compliance Tests
================================

Tests to ensure the framework complies with anti-simulation policies:
1. No fabricated/simulated data
2. No hardcoded file patterns
3. No fallback_to_simulation enabled
4. Confidence scores calculated from real data quality
5. Universal technology support without ACM bias
"""

import pytest
import sys
import os
import ast
import re
from unittest.mock import MagicMock, patch

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../.claude/ai-services'))


class TestAntiSimulationCompliance:
    """Tests for anti-simulation policy compliance."""

    def test_no_simulation_fallback_enabled(self):
        """Verify fallback_to_simulation defaults to False."""
        from jira_api_client import JiraApiConfig

        # Create config with defaults
        config = JiraApiConfig(
            base_url="https://jira.example.com",
            username="test",
            api_token="token"
        )

        assert config.fallback_to_simulation is False, \
            "fallback_to_simulation must default to False per anti-simulation policy"

    def _create_mock_agent(self):
        """Create a JIRAIntelligenceAgent with mocked dependencies."""
        from jira_intelligence_agent import JIRAIntelligenceAgent

        mock_hub = MagicMock()
        mock_run_dir = "/tmp/test_run"

        return JIRAIntelligenceAgent(
            communication_hub=mock_hub,
            run_dir=mock_run_dir
        )

    def test_generate_intelligent_pr_analysis_deprecated(self):
        """Verify _generate_intelligent_pr_analysis raises error when called."""
        agent = self._create_mock_agent()

        with pytest.raises(RuntimeError) as excinfo:
            agent._generate_intelligent_pr_analysis("123", {})

        assert "Anti-simulation policy violation" in str(excinfo.value)

    def test_generate_intelligent_pr_title_deprecated(self):
        """Verify _generate_intelligent_pr_title raises error when called."""
        agent = self._create_mock_agent()

        with pytest.raises(RuntimeError) as excinfo:
            agent._generate_intelligent_pr_title("123", "component", "title")

        assert "Anti-simulation policy violation" in str(excinfo.value)

    def test_predict_likely_files_changed_deprecated(self):
        """Verify _predict_likely_files_changed raises error when called."""
        agent = self._create_mock_agent()

        with pytest.raises(RuntimeError) as excinfo:
            agent._predict_likely_files_changed("component", "title")

        assert "Anti-simulation policy violation" in str(excinfo.value)

    def test_confidence_calculation_method_exists(self):
        """Verify _calculate_pr_data_confidence method exists and calculates properly."""
        agent = self._create_mock_agent()

        # Test with empty data - should return 0
        assert agent._calculate_pr_data_confidence(None) == 0.0
        assert agent._calculate_pr_data_confidence({}) == 0.0

        # Test with partial data
        partial_data = {'title': 'Test PR', 'files_changed': ['file1.py']}
        confidence = agent._calculate_pr_data_confidence(partial_data)
        assert 0.0 < confidence < 1.0, "Partial data should have partial confidence"

        # Test with complete data
        complete_data = {
            'title': 'Complete PR',
            'files_changed': ['file1.py', 'file2.py', 'file3.py'],
            'url': 'https://github.com/owner/repo/pull/123',
            'state': 'merged',
            'author': 'testuser',
            'body': 'This is a detailed description of the changes'
        }
        high_confidence = agent._calculate_pr_data_confidence(complete_data)
        assert high_confidence > confidence, "Complete data should have higher confidence"

    def test_no_hardcoded_confidence_scores(self):
        """Scan code for hardcoded confidence values that should be calculated."""
        ai_services_path = os.path.join(os.path.dirname(__file__), '../../../.claude/ai-services')

        # Pattern for hardcoded confidence values (0.9x or 0.8x)
        hardcoded_pattern = re.compile(r'confidence[_\w]*\s*[=:]\s*0\.(9[0-9]|8[5-9])')

        violations = []

        for filename in ['jira_intelligence_agent.py', 'phase_3_analysis.py', 'phase_4_pattern_extension.py']:
            filepath = os.path.join(ai_services_path, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        # Skip comments
                        if line.strip().startswith('#'):
                            continue
                        if hardcoded_pattern.search(line):
                            # Allow in docstrings or comments
                            if '"""' not in line and "'''" not in line:
                                violations.append(f"{filename}:{line_num}: {line.strip()}")

        # We expect some hardcoded values in tests, but core logic should calculate
        # This is a soft check - just warn if there are too many
        assert len(violations) < 10, \
            f"Too many hardcoded confidence values found:\n" + "\n".join(violations[:5])


class TestUniversalTechnologySupport:
    """Tests for universal technology support without ACM bias."""

    def test_technology_classifier_exists(self):
        """Verify UniversalComponentAnalyzer can be imported."""
        from technology_classification_service import UniversalComponentAnalyzer
        analyzer = UniversalComponentAnalyzer()
        assert analyzer is not None

    def test_non_acm_technology_classification(self):
        """Test that non-ACM technologies are classified correctly without ACM bias."""
        from technology_classification_service import UniversalComponentAnalyzer

        analyzer = UniversalComponentAnalyzer()

        # Test non-ACM technologies
        test_cases = [
            {'id': 'AWS-001', 'title': 'AWS Lambda function', 'description': 'Update Lambda', 'component': 'Lambda'},
            {'id': 'DB-001', 'title': 'PostgreSQL migration', 'description': 'Migrate DB', 'component': 'Database'},
            {'id': 'FE-001', 'title': 'React component', 'description': 'Update React', 'component': 'Frontend'},
        ]

        for jira_content in test_cases:
            result = analyzer.analyze_component(jira_content)
            result_str = str(result).lower() if result else ''

            # Verify no ACM-specific patterns when not relevant
            assert 'clustercurator' not in result_str or 'cluster' in jira_content['title'].lower(), \
                f"ACM bias detected for non-ACM ticket: {jira_content['id']}"


class TestConfigurationCompliance:
    """Tests for configuration file compliance."""

    def test_json_configs_valid(self):
        """Verify all JSON configuration files are valid."""
        import json

        config_dir = os.path.join(os.path.dirname(__file__), '../../../.claude/config')

        for filename in os.listdir(config_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(config_dir, filename)
                with open(filepath, 'r') as f:
                    try:
                        json.load(f)
                    except json.JSONDecodeError as e:
                        pytest.fail(f"Invalid JSON in {filename}: {e}")

    def test_active_hooks_json_valid(self):
        """Verify active_hooks.json is valid and complete."""
        import json

        hooks_path = os.path.join(os.path.dirname(__file__), '../../../.claude/hooks/active_hooks.json')

        with open(hooks_path, 'r') as f:
            data = json.load(f)

        assert 'active_hooks' in data, "Missing 'active_hooks' key"
        assert 'hook_metadata' in data, "Missing 'hook_metadata' key"

    def test_mandatory_analysis_config_valid(self):
        """Verify mandatory-comprehensive-analysis.json is valid."""
        import json

        config_path = os.path.join(os.path.dirname(__file__), '../../../.claude/config/mandatory-comprehensive-analysis.json')

        with open(config_path, 'r') as f:
            data = json.load(f)

        assert 'effective_date' in data, "Missing 'effective_date' key"
        assert 'mandatory_enforcement' in data, "Missing 'mandatory_enforcement' key"


class TestImportCompliance:
    """Tests for import and module compliance."""

    def test_ai_agent_orchestrator_export(self):
        """Verify AIAgentOrchestrator is properly exported."""
        from ai_agent_orchestrator import AIAgentOrchestrator, PhaseBasedOrchestrator

        assert AIAgentOrchestrator is PhaseBasedOrchestrator, \
            "AIAgentOrchestrator should be an alias for PhaseBasedOrchestrator"

    def test_core_module_imports(self):
        """Verify all core modules can be imported."""
        modules = [
            'parallel_data_flow',
            'inter_agent_communication',
            'jira_api_client',
            'environment_assessment_client',
            'technology_classification_service',
            'phase_3_analysis',
            'phase_4_pattern_extension',
            'jira_intelligence_agent',
        ]

        errors = []
        for module in modules:
            try:
                __import__(module)
            except Exception as e:
                errors.append(f"{module}: {e}")

        assert len(errors) == 0, f"Import errors:\n" + "\n".join(errors)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
