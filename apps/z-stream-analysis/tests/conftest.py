"""
Shared test fixtures for z-stream-analysis regression and integration tests.
"""

import json
from pathlib import Path

import pytest
import yaml


@pytest.fixture(scope="session")
def app_root():
    """Root directory of the z-stream-analysis app."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def playbook_dir(app_root):
    """Path to feature playbook YAML files."""
    return app_root / "src" / "data" / "feature_playbooks"


@pytest.fixture(scope="session")
def schema_path(app_root):
    """Path to analysis_results_schema.json."""
    return app_root / "src" / "schemas" / "analysis_results_schema.json"


@pytest.fixture(scope="session")
def schema_data(schema_path):
    """Parsed analysis_results_schema.json."""
    return json.loads(schema_path.read_text())


@pytest.fixture(scope="session")
def base_playbook_data(playbook_dir):
    """Parsed base.yaml content."""
    path = playbook_dir / "base.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def version_playbook_data(playbook_dir):
    """Parsed acm-2.16.yaml content."""
    path = playbook_dir / "acm-2.16.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def all_playbook_profiles(base_playbook_data, version_playbook_data):
    """Merged profiles from base + version overlay."""
    profiles = dict(base_playbook_data.get("profiles", {}))
    profiles.update(version_playbook_data.get("profiles", {}))
    return profiles


@pytest.fixture(scope="session")
def playbook_service(playbook_dir):
    """Initialized FeatureKnowledgeService with real playbooks loaded."""
    from src.services.feature_knowledge_service import FeatureKnowledgeService

    svc = FeatureKnowledgeService(data_dir=str(playbook_dir))
    svc.load_playbooks(acm_version="2.16")
    return svc


@pytest.fixture(scope="session")
def synthetic_analysis_path(app_root):
    """Path to synthetic analysis-results.json fixture."""
    return app_root / "tests" / "fixtures" / "synthetic_analysis_results.json"


@pytest.fixture(scope="session")
def synthetic_analysis(synthetic_analysis_path):
    """Parsed synthetic analysis-results.json."""
    return json.loads(synthetic_analysis_path.read_text())
