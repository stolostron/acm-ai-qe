# Enhanced Test Cases Template - Consistency Enforcement Framework

## MANDATORY STRUCTURE ENFORCEMENT

### STANDALONE TEST CASE REQUIREMENTS
```yaml
standalone_test_case_structure:
  each_test_case_must_include:
    - complete_description: "Full business context and testing purpose for THIS specific test case"
    - standalone_prerequisites: "All environment setup needed for THIS test case only"
    - independent_setup: "Complete setup commands and verification for THIS test case"
    - self_contained_steps: "All steps needed to execute THIS test case independently"
    - standalone_cleanup: "Cleanup commands specific to THIS test case"
    
enforcement_rule: "Every test case MUST be executable without reading any other test case or shared sections"
```

### Test Case Header Requirements (Per Individual Test Case)
```yaml
mandatory_fields_per_test_case:
  - description: "Complete business context and testing purpose for THIS specific scenario"
  - primary_coverage: "Main components being tested in THIS test case"
  - secondary_coverage: "Supporting/integration components for THIS test case"
  - related_jira_tickets: "Linked tickets relevant to THIS test case"
  - test_scope: "Specific scope and boundaries for THIS test case"
```

### Setup Section Requirements (Per Individual Test Case)
```yaml
mandatory_fields_per_test_case:
  - prerequisites: "Environment verification commands with expected outputs for THIS test case"
  - environment_config: "Complete configuration details needed for THIS test case"
  - rbac_setup: "RBAC user creation with specific scripts for THIS test case"
  - verification_commands: "Commands to verify environment readiness for THIS test case"
```

### Test Steps Table Requirements
```yaml
mandatory_columns:
  - step: "Sequential step number"
  - action: "MUST start with 'What We're Doing:' followed by business context"
  - expected_result: "Specific concrete expectations (yes/no/specific values)"
  - sample_commands_ui_navigation: "CLI commands, UI navigation, expected outputs"
```

### MANDATORY TABLE FORMAT
```markdown
| Step | Action | Expected Result | Sample Commands/UI Navigation |
|------|--------|----------------|-------------------------------|
| 1 | **What We're Doing**: [Business context explaining WHY this step matters]<br><br>**CLI**: `[specific CLI command]`<br>**UI**: [specific UI navigation] | **Expected**: [concrete expectation - yes/no/specific value]<br>**Output shows**: `[expected command output]` | ```bash<br>[sample command]<br># Expected: [expected output]<br>``` |
| 2 | **What We're Doing**: [Business context for step 2]<br><br>**CLI**: `[CLI command 2]`<br>**UI**: [UI navigation 2] | **Expected**: [concrete expectation 2] | ```bash<br>[sample command 2]<br>``` |
```

## CONTENT VALIDATION RULES

### FORBIDDEN PATTERNS (Auto-Reject)
```python
FORBIDDEN_PATTERNS = [
    "Based on role configuration",       # Vague expectations
    "performance.*test",                 # No performance testing  
    "stress.*test",                      # No stress testing
    "load.*test",                        # No load testing
    "scale.*test",                       # No scale testing
    "<CLUSTER_.*>",                     # No env-specific in test cases
    "depending on.*",                   # Vague dependencies
    "according to.*configuration"       # Non-specific configuration refs
]
```

### REQUIRED PATTERNS (Auto-Enforce)
```python
REQUIRED_PATTERNS = [
    r"What We're Doing:.*[Tt]esting",   # Mandatory business explanations
    r"Expected.*:(.*yes|no|\w+)",       # Concrete expectations
    r"CLI.*:.*oc.*",                    # Specific CLI commands
    r"UI.*:.*Navigate",                 # Specific UI instructions
    r"kubeadmin.*<CLUSTER_CONSOLE_PASSWORD>.*<CLUSTER_CONSOLE_URL>" # Login standardization
]
```

### BUSINESS CONTEXT REQUIREMENTS
```yaml
test_step_action_format:
  pattern: "What We're Doing: [Business context explaining WHY this test step matters] **CLI**: [commands] **UI**: [navigation] **Expected**: [specific result]"
  
role_justification_requirements:
  - "[Role] needs [action] access for [business purpose]"
  - "[Admin role] requires full [feature] management capabilities"  
  - "[View role] should only see permitted [resources]"
  - "[Operator role] need cross-cluster permissions for [workflow] operations"
```

## ENVIRONMENT HANDLING RULES

### Test Cases File: ALWAYS Environment-Agnostic
```yaml
placeholder_usage:
  cluster_console: "<CLUSTER_CONSOLE_URL>"
  cluster_password: "<CLUSTER_CONSOLE_PASSWORD>"
  test_clusters: "<TEST_CLUSTER_1>", "<TEST_CLUSTER_2>"
  test_domains: "<TEST_DOMAIN>"
  test_users: "<TEST_USER>@<TEST_DOMAIN>"
```

### Complete Analysis File: ALWAYS Environment-Specific
```yaml
specific_details_required:
  test_environment: "actual.domain.com"
  console_url: "https://console-openshift-console.apps.actual.domain.com"
  acm_version: "2.14.0 (Target: 2.15+ required)"
  openshift_version: "Captured during environment assessment OR 'Not captured'"
```

## E2E FEATURE TESTING FOCUS ENFORCEMENT

### E2E Feature Testing ONLY
```yaml
testing_scope:
  allowed:
    - Feature functionality validation
    - Cross-component integration workflows
    - User access and permission verification (when applicable)
    - Error handling and recovery scenarios
    - Component integration scenarios (when applicable)
  
  forbidden:
    - Performance benchmarking
    - Stress testing under load
    - Concurrent user scenarios
    - Response time measurements
    - Scale testing (large datasets/high volume)
```

### Login Instructions Standardization
```yaml
mandatory_login_step:
  pattern: |
    | 1 | Login to ACM Hub Cluster | Successfully authenticated to hub with admin privileges | 
    **CLI**: `oc login --insecure-skip-tls-verify -u kubeadmin -p <CLUSTER_CONSOLE_PASSWORD> <CLUSTER_CONSOLE_URL>`
    **UI**: Navigate to `<CLUSTER_CONSOLE_URL>` → Login with kubeadmin credentials
    **Expected Output**: `Login successful. You have access to XX projects.`
    **Verify Login**: `oc whoami` returns `kubeadmin` |
```

## PERMISSION EXPECTATIONS CLARITY

### Feature-Specific Permission Expectations (When Applicable)
```yaml
feature_permission_examples:
  primary_action: "yes ([Role] needs [action] access for [business justification])"
  secondary_action: "yes ([Role] handles [workflow] operations as core responsibility)"
  cross_cluster_action: "yes ([Role] performs cross-cluster [operations] workflows)"
  restricted_action: "no (if role is [role], not admin - scoped permissions)"
  scoped_access: "no (if [resource]-specific names were specified in assignment)"
```

### Permission Test Patterns (For RBAC Features)
```yaml
permission_validation_format:
  positive_test: 'oc auth can-i [action] [resource] --as=[user] --context [cluster]'
  expected_positive: 'Expected: `yes` ([business justification for why user needs this])'
  negative_test: 'oc auth can-i [forbidden-action] [resource] --as=[user] --context [cluster]' 
  expected_negative: 'Expected: `no` ([scoping rationale])'
```

## COMPLETE TABLE FORMAT EXAMPLE

### Universal Test Case Template (Generated Dynamically)

**NOTE**: This template is populated dynamically based on component analysis. The example below shows the structure - actual content varies by technology.

```markdown
## Test Case 1: Verify {COMPONENT_NAME} {FUNCTIONALITY_TYPE} Functionality

### Description
**What We're Doing**: Validate {COMPONENT_NAME} {FEATURE_DESCRIPTION} for {USE_CASE_CONTEXT}.

### Prerequisites
- {PLATFORM} cluster with {COMPONENT_NAME} {COMPONENT_TYPE} installed
- Administrative access to cluster (kubeadmin credentials)
- {TECHNOLOGY_STACK} deployed with {COMPONENT_NAME}-controller active

### Test Setup
```bash
# Environment Verification
{CLI_TOOL} get {RESOURCE_TYPE} -A
{CLI_TOOL} get nodes --no-headers | wc -l

# Test Preparation
{CLI_TOOL} new-project test-{COMPONENT_NAME}-1 || {CLI_TOOL} project test-{COMPONENT_NAME}-1
```

### Test Steps

| Step | Action | Expected Result | Sample Commands/UI Navigation |
|------|--------|----------------|-------------------------------|
| 1 | **What We're Doing**: Validate cluster access and verify {COMPONENT_NAME} {COMPONENT_TYPE} availability for {TESTING_PURPOSE}<br><br>**CLI**: `{CLI_TOOL} get {RESOURCE_TYPE} -A`<br>**UI**: Navigate to Administration → Custom Resource Definitions → Search "{RESOURCE_TYPE}" | **Expected**: Command returns existing {COMPONENT_NAME} resources OR "No resources found" (both acceptable)<br>**Output shows**: {COMPONENT_TYPE} definition present | ```bash<br>{CLI_TOOL} get {RESOURCE_TYPE} -A<br># Expected: List of resources or "No resources found"<br>{CLI_TOOL} explain {RESOURCE_TYPE}.spec.{PRIMARY_FIELD}<br># Expected: Field description showing {FIELD_PURPOSE}<br>``` |
| 2 | **What We're Doing**: Create test {COMPONENT_NAME} with {FEATURE_CONFIG} to enable {NEW_FUNCTIONALITY}<br><br>**CLI**: `{CLI_TOOL} apply -f {RESOURCE_TYPE}.yaml`<br>**UI**: Navigate to Installed Operators → {OPERATOR_NAME} → {COMPONENT_NAME} → Create Instance | **Expected**: {COMPONENT_NAME} resource created successfully<br>**Output shows**: `{RESOURCE_TYPE}.{API_GROUP}/test-{COMPONENT_NAME} created` | ```yaml<br>apiVersion: {API_GROUP}/{API_VERSION}<br>kind: {COMPONENT_NAME}<br>metadata:<br>  annotations:<br>    {ANNOTATION_KEY}: "{ANNOTATION_VALUE}"<br>``` |

### Cleanup
```bash
# Remove test {COMPONENT_NAME}
{CLI_TOOL} delete {RESOURCE_TYPE} test-{COMPONENT_NAME} -n test-{COMPONENT_NAME}-1

# Cleanup test environment
{CLI_TOOL} delete project test-{COMPONENT_NAME}-1

# Verify cleanup
{CLI_TOOL} get projects &#124; grep test-{COMPONENT_NAME}-1 &#124;&#124; echo "Cleanup successful"
```
```

### Template Variables Reference

The template system automatically substitutes these variables based on component analysis:

- `{COMPONENT_NAME}`: Analyzed component name (e.g., "ClusterCurator", "IngressController", "DatabaseCluster")
- `{FUNCTIONALITY_TYPE}`: Feature category (e.g., "Digest-Based Upgrade", "Traffic Routing", "Backup")
- `{FEATURE_DESCRIPTION}`: Specific feature being tested
- `{USE_CASE_CONTEXT}`: Business context (e.g., "disconnected environments", "high availability scenarios")
- `{PLATFORM}`: Detected platform (OpenShift, Kubernetes, etc.)
- `{COMPONENT_TYPE}`: Component classification (CRD, Controller, Operator, etc.)
- `{TECHNOLOGY_STACK}`: Technology ecosystem (ACM, Kubernetes, Database, etc.)
- `{CLI_TOOL}`: Appropriate CLI tool (oc, kubectl, etc.)
- `{RESOURCE_TYPE}`: Kubernetes resource type (lowercase)
- `{TESTING_PURPOSE}`: Specific testing objective
- `{API_GROUP}`: Kubernetes API group
- `{API_VERSION}`: API version
- `{OPERATOR_NAME}`: Operator/product name for UI navigation
- `{PRIMARY_FIELD}`: Main configuration field
- `{FIELD_PURPOSE}`: Purpose of the configuration field
- `{FEATURE_CONFIG}`: Feature-specific configuration
- `{NEW_FUNCTIONALITY}`: New capability being tested
- `{ANNOTATION_KEY}`: Feature annotation key
- `{ANNOTATION_VALUE}`: Feature annotation value

## INTEGRATION WITH PHASE 4 PROCESSING

### Template Application Trigger Points
```yaml
phase_4_integration:
  trigger_condition: "Phase 3 data available + Phase 4 pattern extension initiated"
  validation_sequence:
    1. "Apply template structure enforcement"
    2. "Run content validation rules engine"
    3. "Execute schema-based structure enforcement"
    4. "Perform business context enhancement"
    5. "Validate final output against quality gates"
```

### Quality Gates
```yaml
quality_gates:
  structure_compliance: "100% (all mandatory sections present)"
  forbidden_pattern_detection: "0 violations"
  required_pattern_presence: "100% (all mandatory patterns found)"
  business_context_completeness: "All test steps have 'What We're Doing' explanations"
  environment_handling_correctness: "Placeholders in test cases, specifics in analysis"
```

## AUTOMATIC ENHANCEMENT RULES

### Vague Language Auto-Fix
```python
AUTO_FIX_PATTERNS = {
    "Based on role configuration": "Specific expectation based on [role] permissions",
    "depending on": "specifically configured for",
    "according to configuration": "as defined in the [specific configuration]",
    "may vary": "should consistently show"
}
```

### Missing Context Auto-Addition
```python
# These are EXAMPLES of context patterns, not fixed injections
CONTEXT_PATTERN_EXAMPLES = {
    "integration_pattern": "Testing [discovered component] integration with [related components] to ensure [business workflow] functions correctly",
    "access_pattern": "Validating [feature] access controls ensure [user roles] have appropriate permissions for [use case]",
    "multi_cluster_pattern": "Verifying [functionality] operates consistently across hub and managed clusters",
    "user_journey_pattern": "Ensuring [user type] can successfully complete [workflow] from start to finish"
}

# The AI adapts these based on the specific feature being tested
```

---

**IMPLEMENTATION NOTE**: This template serves as the enforcement specification for the template-driven generation system. All test case generation MUST validate against these rules before delivery.