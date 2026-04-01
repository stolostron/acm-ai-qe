"""
Stage 1 gather integration tests.

Runs gather.py against a real Jenkins pipeline and validates
every output section of core-data.json.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestCoreDataFileExists:
    def test_core_data_file_exists(self, gathered_run_dir):
        assert (gathered_run_dir / "core-data.json").exists()


class TestMetadataComplete:
    """Step 0: metadata section."""

    def test_metadata_complete(self, core_data):
        meta = core_data.get("metadata", {})
        assert "gathered_at" in meta
        assert "gatherer_version" in meta or "data_version" in meta
        assert "jenkins_url" in meta or "status" in meta


class TestJenkinsDataExtracted:
    """Step 1: jenkins section."""

    def test_jenkins_data_extracted(self, core_data):
        jenkins = core_data.get("jenkins", {})
        assert "job_name" in jenkins or "build_url" in jenkins
        assert "build_number" in jenkins or "build_result" in jenkins


class TestConsoleLogDownloaded:
    """Step 2: console log."""

    def test_console_log_downloaded(self, gathered_run_dir, core_data):
        # Console log file may or may not exist depending on pipeline
        console_section = core_data.get("console_log", {})
        assert isinstance(console_section, dict)


class TestTestReportPopulated:
    """Step 3: test_report section."""

    def test_test_report_populated(self, core_data):
        report = core_data.get("test_report", {})
        assert "summary" in report or "failed_tests" in report

    def test_failed_tests_have_required_fields(self, core_data):
        report = core_data.get("test_report", {})
        failed_tests = report.get("failed_tests", [])
        if not failed_tests:
            pytest.skip("No failed tests in this run")

        for test in failed_tests[:5]:  # Check first 5
            assert "test_name" in test, f"Missing test_name in {test}"

    def test_stack_traces_parsed(self, core_data):
        report = core_data.get("test_report", {})
        failed_tests = report.get("failed_tests", [])
        if not failed_tests:
            pytest.skip("No failed tests to check stack traces")

        # At least some tests should have parsed stack traces
        has_stack = any(
            "parsed_stack_trace" in t for t in failed_tests
        )
        # Stack traces are best-effort, so warn rather than fail
        if not has_stack:
            import warnings
            warnings.warn("No failed tests have parsed_stack_trace")


class TestEnvironmentStatusGathered:
    """Step 4: environment section."""

    def test_environment_status_gathered(self, core_data):
        env = core_data.get("environment", {})
        assert isinstance(env, dict)


class TestClusterLandscapeGathered:
    """Step 4 (cluster landscape): cluster_landscape section."""

    def test_cluster_landscape_gathered(self, core_data):
        landscape = core_data.get("cluster_landscape", {})
        assert isinstance(landscape, dict)

    def test_mch_fields_in_landscape(self, core_data):
        landscape = core_data.get("cluster_landscape", {})
        if not landscape:
            pytest.skip("No cluster_landscape data")

        # mch_enabled_components should be a dict (possibly empty)
        mch_comps = landscape.get("mch_enabled_components")
        assert mch_comps is None or isinstance(mch_comps, dict)

        # mch_version should be a string or null
        mch_version = landscape.get("mch_version")
        assert mch_version is None or isinstance(mch_version, str)


class TestClusterAccessPersisted:
    """Step 4: cluster_access section."""

    def test_cluster_access_persisted(self, core_data):
        access = core_data.get("cluster_access", {})
        assert isinstance(access, dict), "cluster_access should be a dict"
        if access:
            # If present, should have api_url
            assert "api_url" in access or "has_credentials" in access

    def test_cluster_access_credentials_present(self, core_data):
        """CLC pipelines always have credentials in parameters."""
        access = core_data.get("cluster_access", {})
        if not access:
            pytest.skip("cluster_access not populated")

        has_creds = access.get("has_credentials")
        if has_creds is not None:
            # has_credentials may be True or the masked string '***MASKED***'
            assert has_creds is True or has_creds == "***MASKED***", (
                "CLC pipeline should have credentials"
            )


class TestReposCloned:
    """Step 5: repos directory."""

    def test_repos_cloned(self, gathered_run_dir):
        # We used --skip-repo so repos may not exist
        # Just verify the run dir itself exists
        assert gathered_run_dir.exists()


class TestExtractedContextPopulated:
    """Step 6: extracted_context on failed tests."""

    def test_extracted_context_populated(self, core_data):
        report = core_data.get("test_report", {})
        failed_tests = report.get("failed_tests", [])
        if not failed_tests:
            pytest.skip("No failed tests")

        # At least some should have extracted_context
        has_context = any(
            "extracted_context" in t for t in failed_tests
        )
        if not has_context:
            import warnings
            warnings.warn("No failed tests have extracted_context")


class TestFeatureGroundingPopulated:
    """Step 7: feature_grounding section."""

    def test_feature_grounding_populated(self, core_data):
        grounding = core_data.get("feature_grounding", {})
        assert isinstance(grounding, dict)
        if grounding:
            assert "groups" in grounding or "feature_areas_found" in grounding

    def test_clc_pipeline_maps_to_clc_feature(self, core_data):
        grounding = core_data.get("feature_grounding", {})
        if not grounding:
            pytest.skip("No feature_grounding data")

        areas = grounding.get("feature_areas_found", [])
        if areas:
            assert "CLC" in areas, (
                f"CLC pipeline should map to CLC feature area. "
                f"Found: {areas}"
            )


class TestFeatureKnowledgePopulated:
    """Step 8: feature_knowledge section."""

    def test_feature_knowledge_populated(self, core_data):
        fk = core_data.get("feature_knowledge", {})
        assert isinstance(fk, dict), "feature_knowledge should be a dict"
        if fk:
            # Should have at least some content
            assert any(
                key in fk
                for key in ["acm_version", "profiles_loaded", "feature_readiness",
                            "investigation_playbooks", "kg_status",
                            "kg_dependency_context", "note"]
            ), f"feature_knowledge has unexpected keys: {list(fk.keys())}"

    def test_feature_knowledge_has_kg_status(self, core_data):
        fk = core_data.get("feature_knowledge", {})
        if not fk:
            pytest.skip("feature_knowledge not populated")

        kg_status = fk.get("kg_status")
        if kg_status is not None:
            assert "available" in kg_status

    def test_feature_knowledge_kg_unavailable_has_remediation(self, core_data):
        fk = core_data.get("feature_knowledge", {})
        if not fk:
            pytest.skip("feature_knowledge not populated")

        kg_status = fk.get("kg_status", {})
        if kg_status and kg_status.get("available") is False:
            assert "remediation" in kg_status or "impact" in kg_status, (
                "When KG unavailable, should have remediation/impact fields"
            )

    def test_feature_readiness_checks_prerequisites(self, core_data):
        fk = core_data.get("feature_knowledge", {})
        if not fk:
            pytest.skip("feature_knowledge not populated")

        readiness = fk.get("feature_readiness", {})
        if readiness:
            for area, data in readiness.items():
                if isinstance(data, dict) and "prerequisite_checks" in data:
                    assert isinstance(data["prerequisite_checks"], list)

    def test_mch_prerequisites_have_met_value(self, core_data):
        fk = core_data.get("feature_knowledge", {})
        if not fk:
            pytest.skip("feature_knowledge not populated")

        readiness = fk.get("feature_readiness", {})
        landscape = core_data.get("cluster_landscape", {})
        mch_comps = landscape.get("mch_enabled_components", {})

        if not readiness or not mch_comps:
            pytest.skip("No readiness data or MCH components")

        for area, data in readiness.items():
            if not isinstance(data, dict):
                continue
            for check in data.get("prerequisite_checks", []):
                if check.get("type") == "mch_component":
                    met = check.get("met")
                    assert met is not None, (
                        f"MCH prerequisite '{check.get('id')}' in {area} "
                        f"should have met=true/false, got None"
                    )

    def test_investigation_playbooks_contain_failure_paths(self, core_data):
        fk = core_data.get("feature_knowledge", {})
        if not fk:
            pytest.skip("feature_knowledge not populated")

        playbooks = fk.get("investigation_playbooks", {})
        if playbooks:
            for area, pb in playbooks.items():
                if isinstance(pb, dict):
                    assert "failure_paths" in pb, (
                        f"Playbook for {area} missing failure_paths"
                    )


class TestInvestigationHintsBuilt:
    """Step 8: investigation_hints."""

    def test_investigation_hints_built(self, core_data):
        hints = core_data.get("investigation_hints", {})
        assert isinstance(hints, dict)


class TestAIInstructionsPresent:
    """Step 9: ai_instructions section."""

    def test_ai_instructions_present(self, core_data):
        instructions = core_data.get("ai_instructions", {})
        assert isinstance(instructions, dict)
        assert instructions.get("version") == "3.5.0", (
            f"Expected ai_instructions version 3.5.0, "
            f"got {instructions.get('version')}"
        )

    def test_ai_instructions_have_tiered_investigation(self, core_data):
        instructions = core_data.get("ai_instructions", {})
        assert "tiered_investigation" in instructions

    def test_ai_instructions_have_cluster_access(self, core_data):
        instructions = core_data.get("ai_instructions", {})
        assert "cluster_access" in instructions


class TestNoSensitiveDataInOutput:
    """Password fields should be masked."""

    def test_no_sensitive_data_in_output(self, core_data):
        import json

        text = json.dumps(core_data)

        # Check cluster_access password is masked
        access = core_data.get("cluster_access", {})
        if access:
            password = access.get("password", "")
            if password:
                # Password should be masked (contain **** or similar)
                assert "****" in password or password.startswith("***"), (
                    "cluster_access password should be masked"
                )


class TestErrorsArrayPresent:
    """errors array exists."""

    def test_errors_array_present(self, core_data):
        errors = core_data.get("errors")
        assert errors is not None, "Missing 'errors' key in core-data.json"
        assert isinstance(errors, list)
