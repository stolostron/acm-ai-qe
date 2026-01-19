# Z-Stream Pipeline Analysis

Enterprise Jenkins pipeline failure analysis with definitive PRODUCT BUG | AUTOMATION BUG | INFRASTRUCTURE classification.

## CRITICAL: Read This First

When you receive a Jenkins URL, follow these steps EXACTLY:

---

## STEP-BY-STEP WORKFLOW

### Step 1: Run Data Gathering Script

```bash
python -m src.scripts.gather "<JENKINS_URL>"
```

Wait for the script to complete. It will output the run directory path.

**What it gathers:**
- Jenkins build info and parameters (credentials masked)
- Console log (full output)
- Test report with per-test failure details
- Environment/cluster health status (uses TARGET cluster from Jenkins params)
- Repository analysis (clones automation repo, indexes selectors, git history)
- Console repo analysis (clones stolostron/console for timeline comparison)
- Timeline comparison (compares git dates between automation and console repos)
- Evidence package with pre-calculated classification scores (hybrid AI + script)

### Step 2: Read the Gathered Data (Multi-File Structure)

Data is split into multiple files to stay under token limits. **Always read core-data.json first:**

```bash
# Primary data file (read this first)
cat runs/<RUN_DIR>/core-data.json
```

**core-data.json contains:**
- `metadata` - Gathering metadata and version info
- `jenkins` - Build info and parameters
- `test_report.failed_tests` - Array of failed tests to analyze
- `console_log.key_errors` - Error messages from console
- `environment` - Cluster health status (target_cluster_used: true/false)
- `evidence_package` - Pre-calculated classification scores per test
- `timeline_comparison` - Git date comparison between repos
- `repository_summary` - Summary of repository analysis (counts only)
- `ai_instructions` - Workflow and schema guidance

**On-demand files (load only when needed):**

```bash
# For element_not_found errors - load selector lookup
cat runs/<RUN_DIR>/repository-selectors.json

# For stack trace analysis - load test file details
cat runs/<RUN_DIR>/repository-test-files.json

# For full repository details
cat runs/<RUN_DIR>/repository-metadata.json
```

**File index:**
```bash
cat runs/<RUN_DIR>/manifest.json
```

### Step 3: Analyze Each Failed Test

For EACH test in `test_report.failed_tests`:

**3a. Read the test details:**
- `test_name` - What test failed
- `error_message` - What went wrong
- `stack_trace` - Where it failed (file:line)
- `failure_type` - Type of failure (timeout, element_not_found, etc.)
- `preliminary_classification` - Script's initial classification
- `preliminary_confidence` - Script's confidence score

**3b. Cross-reference with repository data:**
- Load `repository-selectors.json` and check `selector_lookup` for the failing selector
- Find which test files use that selector
- Look for similar/alternative selectors

**3c. Classify the test:**

| Classification | When to Use |
|----------------|-------------|
| `PRODUCT_BUG` | Backend error (500), API broken, feature doesn't work |
| `AUTOMATION_BUG` | Selector not found, timeout on wait, test logic wrong |
| `INFRASTRUCTURE` | Cluster down, network error, provisioning failed |

**3d. Document your reasoning:**
- What evidence supports your classification?
- What's your confidence (0-100%)?

**3e. Recommend a fix:**
- Specific action to resolve
- Who should fix it (automation team, product team, platform team)

### Step 4: Create analysis-results.json

Save your analysis to `runs/<RUN_DIR>/analysis-results.json`:

```json
{
  "analysis_metadata": {
    "jenkins_url": "<URL>",
    "analyzed_at": "2026-01-15T15:00:00Z",
    "build_result": "UNSTABLE",
    "branch": "release-2.12"
  },
  "per_test_analysis": [
    {
      "test_name": "...",
      "classification": "PRODUCT_BUG|AUTOMATION_BUG|INFRASTRUCTURE",
      "confidence": 0.85,
      "reasoning": "...",
      "evidence": ["..."],
      "recommended_fix": "...",
      "owner": "Product Team|Automation Team|Platform Team",
      "priority": "CRITICAL|HIGH|MEDIUM|LOW"
    }
  ],
  "summary": {
    "total_failures": 2,
    "by_classification": {
      "PRODUCT_BUG": 0,
      "AUTOMATION_BUG": 1,
      "INFRASTRUCTURE": 1
    },
    "overall_classification": "AUTOMATION_BUG",
    "overall_confidence": 0.85
  }
}
```

#### Schema Requirements

**Required fields:**
- `per_test_analysis` - Array with `test_name`, `classification`, `confidence` per test
- `summary.by_classification` - Object with classification counts

**Recommended fields:**
- `reasoning` - Why this classification was chosen
- `recommended_fix` - Specific action to resolve
- `summary.overall_classification` - Dominant classification
- `summary.overall_confidence` - Overall confidence score

**Template file:** `src/schemas/analysis_results_template.json`
**JSON Schema:** `src/schemas/analysis_results_schema.json`

The report script validates analysis-results.json and shows warnings for missing fields.

### Step 5: Generate Reports

```bash
python -m src.scripts.report runs/<RUN_DIR>
```

### Step 6: Present Summary

Display the results to the user with:
- Total failures and pass rate
- Classification breakdown
- Top priority actions

---

## ARCHITECTURE

### 2-Agent Intelligence Framework

```
Jenkins URL
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 1: DATA GATHERING (gather.py)                   │
│  - Jenkins API (via MCP or curl)                       │
│  - Console log extraction                              │
│  - Test report parsing (per-test details)              │
│  - Target cluster validation (oc login)                │
│  - Repository clone and selector indexing              │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 2: INVESTIGATION AGENT                          │
│  (InvestigationIntelligenceAgent)                      │
│  - Per-test failure analysis with classification       │
│  - Environment validation (real oc/kubectl commands)   │
│  - Repository analysis (real git clone)                │
│  - Evidence correlation across sources                 │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 3: SOLUTION AGENT                               │
│  (SolutionIntelligenceAgent)                           │
│  - Bug classification (per-test + overall)             │
│  - Fix recommendations with priorities                 │
│  - Implementation guidance                             │
└────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────┐
│  PHASE 4: REPORT GENERATION (report.py)                │
│  - Detailed-Analysis.md (human-readable)               │
│  - SUMMARY.txt (console-friendly)                      │
│  - analysis-results.json (machine-readable)            │
└────────────────────────────────────────────────────────┘
```

### Services Layer

| Service | File | Purpose |
|---------|------|---------|
| JenkinsIntelligenceService | `jenkins_intelligence_service.py` | Build info, test reports, per-test classification |
| JenkinsMCPClient | `jenkins_mcp_client.py` | MCP integration for Jenkins API |
| EnvironmentValidationService | `environment_validation_service.py` | Real oc/kubectl cluster validation (READ-ONLY) |
| RepositoryAnalysisService | `repository_analysis_service.py` | Git clone, test file indexing, selector lookup, git history |
| TwoAgentIntelligenceFramework | `two_agent_intelligence_framework.py` | 2-agent orchestration |
| EvidenceValidationEngine | `evidence_validation_engine.py` | Claim validation, false positive detection |
| ReportGenerator | `report_generator.py` | Multi-format report generation |

### Classification Services (Hybrid AI + Script)

| Service | File | Purpose |
|---------|------|---------|
| StackTraceParser | `stack_trace_parser.py` | Parse stack traces to extract file:line, root cause frame |
| ClassificationDecisionMatrix | `classification_decision_matrix.py` | Formal rules for classification based on failure type, env health, selector status |
| ConfidenceCalculator | `confidence_calculator.py` | Multi-factor confidence scoring (5 factors, weighted) |
| CrossReferenceValidator | `cross_reference_validator.py` | Catch misclassifications, apply correction rules |
| EvidencePackageBuilder | `evidence_package_builder.py` | Build structured evidence packages per test |
| ASTIntegrationService | `ast_integration_service.py` | Optional Node.js AST helper for selector resolution |
| TimelineComparisonService | `timeline_comparison_service.py` | Compare git modification dates between automation and console repos |

### Shared Utilities

The `shared_utils.py` module provides common functions to avoid code duplication:

| Function | Purpose |
|----------|---------|
| `run_subprocess` | Standardized subprocess execution with timeout handling |
| `build_curl_command` / `execute_curl` | HTTP requests with optional auth |
| `parse_json_response` / `safe_json_loads` | JSON parsing with HTML detection |
| `get_jenkins_credentials` / `encode_basic_auth` | Credential handling |
| `is_test_file` / `is_framework_file` | File type detection |
| `mask_sensitive_value` / `mask_sensitive_dict` | Credential masking (used by gather.py) |
| `ServiceBase` | Base class for services with logging and common methods |

The `stack_trace_parser.py` provides `extract_failing_selector()` which is used by gather.py for consistent selector extraction.

---

## AUTHENTICATION

### Jenkins Authentication Priority

1. **MCP Server** (if configured in `~/.cursor/mcp.json`)
2. **Environment Variables**: `JENKINS_USER` + `JENKINS_API_TOKEN`
3. **Constructor Arguments**

### Target Cluster Authentication

The gather script extracts target cluster credentials from Jenkins build parameters:

| Parameter Names Checked |
|------------------------|
| `CYPRESS_HUB_API_URL` / `CLUSTER_API_URL` / `API_URL` |
| `CYPRESS_OPTIONS_HUB_USER` / `CLUSTER_USER` / `USERNAME` |
| `CYPRESS_OPTIONS_HUB_PASSWORD` / `CLUSTER_PASSWORD` / `PASSWORD` |

If found, the script:
1. Creates a temporary kubeconfig
2. Runs `oc login` to the target cluster
3. Validates environment against the TARGET cluster (not local kubeconfig)
4. Cleans up temporary kubeconfig after validation

Check `environment.target_cluster_used` in core-data.json to confirm.

---

## SECURITY FEATURES

### Credential Masking

All sensitive data is masked before saving to files:

| Pattern | Example Original | Example Masked |
|---------|-----------------|----------------|
| `*PASSWORD*` | `QIEe7-dYHRh-5I4jw` | `QIE***MASKED***` |
| `*TOKEN*` | `kYuKAlDIc1qHlC02` | `kYu***MASKED***` |
| `*SECRET*` | `my-api-secret` | `my-***MASKED***` |
| `*KEY*` | `api-key-12345` | `api***MASKED***` |
| `*CREDENTIAL*` | `cred-value` | `***MASKED***` |

### READ-ONLY Cluster Operations

Only whitelisted commands are allowed:
- `login`, `logout`, `whoami`, `cluster-info`, `version`
- `get`, `describe`, `api-resources`
- `auth can-i` (permission checks)
- `config current-context`, `config get-contexts`, `config view`

Any other command is blocked with: `Command blocked: READ-ONLY mode violation`

---

## CLASSIFICATION QUICK REFERENCE

### PRODUCT_BUG
- Server returns 500, 502, 503 errors
- API response doesn't match expected
- UI feature broken or missing
- Data validation fails on valid data

### AUTOMATION_BUG
- `Element not found` - selector changed
- `Timeout waiting for` - need better wait
- Test data/fixtures incorrect
- Auth token expired

### INFRASTRUCTURE
- `Connection refused` - cluster down
- `Cluster stuck in Pending` - provisioning failed
- `DNS resolution failed` - network issue
- Timeout during cluster operations

---

## HYBRID CLASSIFICATION SYSTEM

The classification system uses a formal decision matrix combined with cross-reference validation for accurate, explainable classifications.

### Decision Matrix

The `ClassificationDecisionMatrix` maps (failure_type, env_healthy, selector_found) to weighted scores:

| Failure Type | Env Healthy | Selector Found | Product | Automation | Infra |
|--------------|-------------|----------------|---------|------------|-------|
| element_not_found | ✓ | ✓ | 30% | 60% | 10% |
| element_not_found | ✓ | ✗ | 60% | 30% | 10% |
| element_not_found | ✗ | ✓ | 20% | 30% | 50% |
| server_error | ✓ | * | 90% | 5% | 5% |
| timeout | ✓ | * | 20% | 70% | 10% |
| timeout | ✗ | * | 10% | 20% | 70% |
| network | ✗ | * | 10% | 10% | 80% |
| network | ✓ | * | 60% | 10% | 30% |

### Additional Factors

These factors modify the base classification:
- `console_500_error`: Boosts PRODUCT_BUG score by 15%
- `selector_recently_changed`: Boosts AUTOMATION_BUG score by 20%
- `cluster_inaccessible`: Boosts INFRASTRUCTURE score by 25%

### Cross-Reference Validation

The `CrossReferenceValidator` catches misclassifications:

| Rule | Condition | Action |
|------|-----------|--------|
| 500 Override | AUTOMATION_BUG + console has 500 errors | Correct → PRODUCT_BUG |
| Cluster Override | AUTOMATION_BUG + cluster unhealthy | Correct → INFRASTRUCTURE |
| Selector Change | PRODUCT_BUG + selector recently changed | Flag for review |
| Network Mismatch | AUTOMATION_BUG + network errors in console | Flag for review |
| Missing Selector | AUTOMATION_BUG + selector not in codebase | Flag for review (not auto-correct) |

**Note on Bias Prevention**: The validator does NOT auto-correct to PRODUCT_BUG when a selector is missing from the codebase. This is because TimelineComparisonService provides more accurate classification by comparing git dates between automation and console repos. Missing selector could be either PRODUCT_BUG (UI changed) or AUTOMATION_BUG (automation using invalid selector) - the timeline comparison determines which.

### Confidence Calculation

Five-factor weighted confidence scoring:

| Factor | Weight | Description |
|--------|--------|-------------|
| Score Separation | 30% | How clearly one classification wins |
| Evidence Completeness | 25% | How much data we have (repo, env, console) |
| Source Consistency | 20% | Do all sources agree on classification |
| Selector Certainty | 15% | Is selector found/not found definitive |
| History Signal | 10% | Does git history support classification |

### Evidence Package Output

The gather script produces `evidence-package.json` with pre-calculated scores:

```json
{
  "test_failures": [{
    "test_name": "test_create_cluster",
    "failure_evidence": {
      "error_type": "AssertionError",
      "failure_category": "element_not_found",
      "root_cause_file": "managedCluster.js",
      "root_cause_line": 181
    },
    "repository_evidence": {
      "selector_found": true,
      "selector_recently_changed": true,
      "days_since_modified": 6
    },
    "environment_evidence": {
      "cluster_healthy": true,
      "api_accessible": true
    },
    "pre_calculated_scores": {
      "product_bug_score": 0.45,
      "automation_bug_score": 0.50,
      "infrastructure_score": 0.05
    },
    "final_classification": "PRODUCT_BUG",
    "final_confidence": 0.72
  }]
}
```

---

## TIMELINE COMPARISON SERVICE

The `TimelineComparisonService` provides definitive classification for "Element not found" errors by comparing git modification dates between the automation repository (clc-ui-e2e) and the product console repository (stolostron/console).

### Core Principle

**Who fell behind determines the bug owner:**

| Console Modified | Automation Modified | Classification | Reasoning |
|-----------------|---------------------|----------------|-----------|
| More recently | Earlier | AUTOMATION_BUG | Automation didn't keep up with UI changes |
| Earlier | More recently | PRODUCT_BUG | UI broke after automation was updated |
| Never existed | N/A | AUTOMATION_BUG | Selector was invalid from the start |
| Removed | Still used | AUTOMATION_BUG | Automation using deleted element |

### How It Works

1. **Clone Console Repo**: During gather, clones `https://github.com/stolostron/console.git` at matching branch
2. **Extract Element ID**: Parses selector (`#google` → `google`, `[data-testid='button']` → `button`)
3. **Check Existence**: Uses `git grep` to check if element exists in console codebase
4. **Get Timelines**: Uses `git log -S` to find last modification date for both repos
5. **Compare Dates**: Determines which repo was modified more recently
6. **Classify**: Applies timeline-based classification logic

### Timeline Data Structure

```json
{
  "timeline_comparison": {
    "console_cloned": true,
    "console_path": "/tmp/console_abc123",
    "branch": "release-2.15"
  },
  "test_failures": [{
    "timeline_analysis": {
      "selector": "#google",
      "element_id": "google",
      "console_timeline": {
        "exists_in_console": false,
        "last_modified_date": "2026-01-01",
        "last_commit_sha": "abc123",
        "last_commit_message": "Remove google branding"
      },
      "automation_timeline": {
        "exists_in_automation": true,
        "last_modified_date": "2025-06-01"
      },
      "classification": "AUTOMATION_BUG",
      "confidence": 0.92,
      "reasoning": "Element 'google' was removed from console on 2026-01-01 but automation still references it",
      "element_removed_from_console": true,
      "days_difference": 214
    }
  }]
}
```

### Timeout Pattern Detection

Multiple timeouts in a single run often indicate infrastructure issues rather than individual test problems:

| Condition | Classification | Confidence |
|-----------|---------------|------------|
| ≥50% of failures are timeouts | INFRASTRUCTURE | 85% |
| Any timeout + unhealthy environment | INFRASTRUCTURE | 90% |
| Single timeout + healthy environment | ELEMENT_SPECIFIC | 70% |

### Integration with Gather Script

The gather script automatically:
1. Clones the console repo after the automation repo
2. For each "Element not found" error, runs timeline comparison
3. Reclassifies if timeline confidence ≥80%
4. Stores timeline analysis in evidence package
5. Cleans up both cloned repos after completion

### Usage in Classification

When the decision matrix returns an ambiguous classification for element_not_found errors, the timeline comparison overrides it:

```python
# If timeline comparison has high confidence, it takes precedence
if comparison.confidence >= 0.80:
    final_classification = comparison.classification  # Use timeline result
else:
    final_classification = decision_matrix_result  # Use decision matrix
```

---

## REPOSITORY ANALYSIS

The gather script automatically:
1. Extracts repo URL from console log (`Checking out git https://...`)
2. Extracts branch from checkout (`origin/release-2.15`)
3. Clones the repository at the correct branch
4. Indexes all test files and selectors
5. Creates a selector lookup for cross-referencing

### Using Selector Lookup

When a test fails with "Element not found", check:

```python
# In repository-selectors.json (load on-demand)
selector_lookup = {
    "#managedClusterSet": ["cypress/views/clusters/managedCluster.js"],
    "button.pf-v6-c-menu-toggle": ["cypress/views/common/dropdown.js"],
    ...
}
```

This helps identify:
- If the selector exists in the codebase
- Which files use that selector
- Alternative selectors that might work

### Repository Data Structure

```json
{
  "repository": {
    "repository_url": "https://github.com/org/repo.git",
    "branch": "release-2.15",
    "commit_sha": "abc123...",
    "repository_cloned": true,
    "test_files": [
      {
        "path": "cypress/tests/example.spec.js",
        "test_framework": "cypress",
        "test_count": 15,
        "selectors": ["#button", ".class", "[data-cy=test]"]
      }
    ],
    "selector_lookup": {
      "#selector": ["file1.js", "file2.js"]
    },
    "dependency_analysis": {
      "framework": "cypress",
      "version": "^13.15.2"
    }
  }
}
```

---

## FILE STRUCTURE

```
z-stream-analysis/
├── main.py                    # Full pipeline orchestration
├── CLAUDE.md                  # This file
├── .claude/
│   ├── settings.json          # Inherits from workspace settings
│   ├── settings.local.json    # Local permissions for commands
│   └── agents/                # Claude Code subagents
│       ├── z-stream-analysis.md           # Main analysis agent
│       ├── investigation-intelligence.md  # Investigation phase agent
│       └── solution-intelligence.md       # Solution phase agent
├── src/
│   ├── schemas/
│   │   ├── __init__.py                   # Schema exports
│   │   ├── analysis_results_schema.json  # JSON Schema (Draft-07)
│   │   ├── analysis_results_template.json # Template for AI
│   │   ├── evidence_package_schema.json  # Evidence package schema
│   │   └── manifest_schema.json          # Multi-file manifest schema
│   ├── scripts/
│   │   ├── gather.py          # Data collection (no analysis)
│   │   └── report.py          # Report generation (with schema validation)
│   └── services/
│       ├── __init__.py                   # Service exports
│       ├── jenkins_intelligence_service.py
│       ├── jenkins_mcp_client.py
│       ├── environment_validation_service.py
│       ├── repository_analysis_service.py
│       ├── two_agent_intelligence_framework.py
│       ├── evidence_validation_engine.py
│       ├── schema_validation_service.py  # JSON schema validation
│       ├── report_generator.py
│       ├── shared_utils.py               # Common utilities (subprocess, masking, etc.)
│       │   # Classification Services (Hybrid AI + Script)
│       ├── stack_trace_parser.py         # Parse stack traces to file:line
│       ├── classification_decision_matrix.py  # Formal classification rules
│       ├── confidence_calculator.py      # Multi-factor confidence scoring
│       ├── cross_reference_validator.py  # Evidence consistency checks
│       ├── evidence_package_builder.py   # Build structured evidence packages
│       ├── ast_integration_service.py    # Optional Node.js AST helper
│       └── timeline_comparison_service.py # Compare git dates between repos
├── tests/
│   ├── deep_dive_validation.py    # Comprehensive 64-test validation
│   ├── e2e_workflow_simulation.py # End-to-end workflow test
│   └── unit/
│       └── services/
│           ├── test_stack_trace_parser.py
│           ├── test_classification_decision_matrix.py
│           ├── test_confidence_calculator.py
│           ├── test_cross_reference_validator.py
│           ├── test_evidence_package_builder.py
│           └── test_timeline_comparison_service.py
└── runs/                      # Analysis outputs
    └── <job>_<timestamp>/
        ├── manifest.json              # File index (multi-file structure)
        ├── core-data.json             # Primary data for AI (~5,500 tokens)
        ├── repository-metadata.json   # Repo summary (~800 tokens)
        ├── repository-test-files.json # Test file details (~7,000 tokens)
        ├── repository-selectors.json  # Selector lookup (~7,500 tokens)
        ├── raw-data.json              # Backward-compat stub (~200 tokens)
        ├── evidence-package.json      # Pre-calculated classification scores
        ├── jenkins-build-info.json    # Build metadata (masked)
        ├── console-log.txt            # Full console output
        ├── test-report.json           # Per-test failure details
        ├── environment-status.json    # Cluster health
        ├── repository-analysis.json   # Full repo data (legacy, use split files instead)
        ├── analysis-results.json   # AI analysis output
        ├── Detailed-Analysis.md    # Human-readable report
        └── SUMMARY.txt             # Brief summary
```

---

## EXAMPLE SESSION

**User:** Analyze https://jenkins.example.com/job/pipeline/123/

**You:**
1. Run: `python -m src.scripts.gather "https://jenkins.example.com/job/pipeline/123/"`
2. Read: `runs/<dir>/core-data.json` (primary data file)
3. For each failed test in `test_report.failed_tests`:
   - Check error message and stack trace
   - If element_not_found, load `repository-selectors.json` for selector lookup
   - Cross-reference with `console_log.key_errors`
   - Classify as PRODUCT_BUG, AUTOMATION_BUG, or INFRASTRUCTURE
4. Save: `analysis-results.json`
5. Run: `python -m src.scripts.report runs/<dir>`
6. Present summary to user

---

## CLI USAGE

### Data Gathering
```bash
# Basic usage
python -m src.scripts.gather <jenkins_url>

# With options
python -m src.scripts.gather --url <jenkins_url> --output-dir ./runs --verbose
python -m src.scripts.gather <jenkins_url> --skip-env    # Skip cluster validation
python -m src.scripts.gather <jenkins_url> --skip-repo   # Skip repository analysis
```

### Report Generation
```bash
python -m src.scripts.report <run_dir>
```

### Full Pipeline
```bash
python main.py <jenkins_url>
python main.py --url <jenkins_url> --output-dir ./runs --verbose --json
```

### Running Tests
```bash
# Comprehensive validation (64 tests across all services)
python3 tests/deep_dive_validation.py

# End-to-end workflow simulation with realistic mock data
python3 tests/e2e_workflow_simulation.py

# Unit tests (requires pytest)
python3 -m pytest tests/unit/services/ -v
```

---

## DATA FLOW DIAGRAM

```
Jenkins URL
    │
    ▼
┌─────────────────────────────────────────┐
│           gather.py                      │
│  ┌─────────┐ ┌─────────┐ ┌───────────┐  │
│  │ Jenkins │ │ Console │ │ Test      │  │
│  │ API     │ │ Log     │ │ Report    │  │
│  └────┬────┘ └────┬────┘ └─────┬─────┘  │
│       │           │            │         │
│       │    ┌──────┴──────┐     │         │
│       │    │ Extract     │     │         │
│       │    │ Repo URL    │     │         │
│       │    │ + Branch    │     │         │
│       │    └──────┬──────┘     │         │
│       │           │            │         │
│  ┌────┴────┐ ┌────┴─────┐ ┌────────────┐│
│  │ Target  │ │ Clone    │ │ Clone      ││
│  │ Cluster │ │ Auto     │ │ Console    ││
│  │ Login   │ │ Repo     │ │ Repo       ││
│  └────┬────┘ └────┬─────┘ └─────┬──────┘│
│       │           │             │        │
│       │    ┌──────┴─────────────┘        │
│       │    │  Timeline Comparison        │
│       │    │  (git log -S dates)         │
│       │    └──────┬──────────────        │
│       │           │                      │
│       └───────────┼──────────────        │
│                   ▼                      │
│         Multi-File Output:               │
│         - manifest.json                  │
│         - core-data.json (primary)       │
│         - repository-selectors.json      │
│         - repository-test-files.json     │
│         - raw-data.json (stub)           │
│         (all credentials masked)         │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│         AI Analysis (Claude)            │
│  - Read core-data.json first            │
│  - Check evidence_package for scores    │
│  - Load selectors on-demand if needed   │
│  - Cross-reference with console_log     │
│  - Classify each failure                │
│  - Document evidence + reasoning        │
└─────────────────────────────────────────┘
                   │
                   ▼
           analysis-results.json
                   │
                   ▼
┌─────────────────────────────────────────┐
│           report.py                      │
│  - Detailed-Analysis.md                 │
│  - SUMMARY.txt                          │
│  - per-test-breakdown.json              │
└─────────────────────────────────────────┘
```

---

## MULTI-FILE DATA STRUCTURE

To stay under Claude Code's 25,000 token limit, data is split into multiple files:

### Token Budget

| File | Est. Tokens | Purpose |
|------|-------------|---------|
| `manifest.json` | ~150 | Index file with file descriptions and workflow |
| `core-data.json` | ~5,500 | Primary analysis data (read this first) |
| `repository-metadata.json` | ~800 | Repository summary without large arrays |
| `repository-test-files.json` | ~7,000 | Test file details with selectors per file |
| `repository-selectors.json` | ~7,500 | Selector lookup for element_not_found debugging |
| `raw-data.json` | ~200 | Backward-compatibility stub |

**All files stay well under the 25,000 token limit.**

### Loading Strategy

1. **Always read `core-data.json` first** - contains all primary analysis data
2. **Load on-demand files only when needed:**
   - `repository-selectors.json` - for element_not_found errors
   - `repository-test-files.json` - for stack trace analysis
   - `repository-metadata.json` - for full repository details

### Backward Compatibility

- Old runs with legacy `raw-data.json` still work
- `report.py` auto-detects file structure
- New stub `raw-data.json` points to `core-data.json`

### Detection Logic

```python
# In report.py
if manifest.json exists:
    # Multi-file mode → load core-data.json
elif raw-data.json has _migration_version:
    # Multi-file stub → load core-data.json
else:
    # Legacy mode → use raw-data.json as-is
```
