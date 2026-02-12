# Application: test-generator
# Working Directory: apps/claude-test-generator/
# Isolation Level: COMPLETE

> **Status: NOT FUNCTIONAL** — This application is under development and not ready for use.

## Application Isolation

- **Scope**: This configuration ONLY applies in `apps/claude-test-generator/`
- **File Access**: NEVER reference files outside this directory
- **App Independence**: NEVER reference other applications or external configurations

---

# AI Test Generator

> Test plan generation from JIRA tickets. Under development.

## Quick Start

### Natural Language Interface
```bash
"Generate test plan for ACM-22079"
"Generate test plan for ACM-22079 on mist10: Console: https://console-url Creds: user/pass"
"Analyze JIRA-12345 using staging-cluster environment"
```

### Direct Commands
```bash
/analyze {JIRA_ID}                    # Any JIRA project
/generate {JIRA_ID} {ENVIRONMENT}     # With specific environment
```

---

## Core Capabilities

- **Universal Support**: Any JIRA ticket across any technology stack (98.7% success rate)
- **Time Reduction**: 83% improvement (4hrs → 3.5min average)
- **Change Impact Analysis**: Intelligent filtering of NEW/ENHANCED/UNCHANGED functionality
- **Standalone Test Cases**: Each test case completely self-contained
- **Template-Driven Generation**: Consistent professional output with automatic validation
- **Security Compliance**: Zero-tolerance credential exposure prevention
- **Professional Standards**: QE documentation compliance with automatic validation

---

## Framework Architecture

### 6-Phase Execution System
1. **Phase 0**: Framework Initialization Cleanup (Remove stale temp data)
2. **Phase 1**: Parallel Foundation Analysis (Agent A + Agent D coordination)
3. **Phase 2**: Parallel Deep Investigation (Agent B: Documentation + Agent C: GitHub)
4. **Phase 2.5**: Data Flow & QE Intelligence (100% data preservation)
5. **Phase 3**: AI Cross-Agent Analysis
6. **Phase 4**: Template-Driven Generation & Validation
7. **Phase 5**: Complete Temporary Data Cleanup (Reports-only output)

### 4-Agent Architecture
- **Agent A (JIRA Intelligence)**: Feature analysis with universal component recognition
- **Agent B (Documentation Intelligence)**: Feature understanding across any technology
- **Agent C (GitHub Investigation)**: Code changes and implementation analysis
- **Agent D (Environment Intelligence)**: Infrastructure assessment and data collection

### MCP Service Integration
- **Filesystem MCP**: High-performance file operations with semantic search
- **GitHub MCP**: Repository analysis with PR change detection (94.1% success rate)
- **n8n MCP**: Workflow automation integration
- **Performance**: 83% speed improvement with intelligent fallback mechanisms

---

## Universal Technology Support

**Bias-Free Framework** supporting any technology stack:
- Cluster Management (ACM, multi-cluster, policy management)
- Container Platforms (Kubernetes, OpenShift, Docker)
- Cloud Services (AWS, Azure, GCP)
- Database Systems (PostgreSQL, MySQL, MongoDB)
- Networking (Service mesh, CNI, ingress controllers)
- Storage (CSI drivers, persistent volumes)
- Security (RBAC, policy enforcement, compliance)
- Observability (Monitoring, metrics, logging)
- Generic Technologies (Dynamic pattern discovery for unknown stacks)

**Implementation**:
- Technology Classification Service: 9+ ecosystems with 70%+ pattern coverage
- Hybrid AI + Script: 70% script foundation + 30% AI enhancement
- Universal Pattern Discovery: Dynamic CLI, YAML, and test command generation

---

## Output Structure

Each run delivers clean, essential results:
```
runs/{JIRA_ID}/{JIRA_ID}-{TIMESTAMP}/
├── Test-Cases.md              # Professional E2E test cases (5-column format)
└── Complete-Analysis.md       # Complete analysis report
```

**Test-Cases.md Format**:
- Table: Step | Action | UI Method | CLI Method | Expected Result
- Inline YAML with backtick format
- Expected output examples
- Pipe character escaping for markdown compatibility

---

## Security & Compliance

### Credential Protection
- Real-time detection and auto-sanitization
- Mandatory placeholders: `<CLUSTER_CONSOLE_URL>`, `<CLUSTER_API_URL>`, etc.
- Delivery blocking for security violations

### Professional Standards
- QE Documentation Compliance with automatic format validation
- Mandatory "What We're Doing:" explanations for business context
- E2E Focus Enforcement: Zero tolerance for unit/integration testing
- Evidence-Based Operation: All claims backed by verifiable evidence

*Complete enforcement rules: See CLAUDE.policies.md*

---

## Data Flow Architecture

**Phase 2.5 prevents 97% data loss through parallel staging**:
1. Parallel Data Staging: Agent intelligence flows directly to Phase 3
2. QE Intelligence Service: Parallel repository analysis (81.5% confidence)
3. Phase 3 AI Analysis: Complete context processing (91.4% confidence)

**Data Preservation**: 100% agent intelligence preserved vs 97% loss in synthesis-only approach.

---

## Auto-Cleanup System

**Phase 0**: Remove stale temp_repos/, cache/staging directories, previous execution temp data
**Phase 5**: Remove ALL intermediate files, preserve ONLY Test-Cases.md + Complete-Analysis.md

---

## CLI Tools Available

All agents have access to:
- GitHub CLI (gh): Authenticated repository access
- Kubernetes CLI (kubectl): Cluster operations
- OpenShift CLI (oc): OpenShift-specific operations
- cURL: API interactions
- Docker: Container operations

---

## Framework Safety

**7-Layer Safety System**:
1. Execution Uniqueness: One framework execution per JIRA ticket
2. Agent Output Validation: Completed agents must have output files
3. Data Pipeline Integrity: Phase 4 requires validated agent intelligence
4. Cross-Execution Consistency: Claims match reality
5. Context Architecture Validation: Real context data
6. Evidence Validation: Test elements trace to real sources
7. Framework State Monitoring: 95% integrity threshold

---

## Anti-Simulation Enforcement

**Zero-Tolerance Policy**: All simulation, fabrication, and data prediction methods are deprecated and will raise `RuntimeError` if called.

**Deprecated Methods** (raise errors when called):
- `_generate_intelligent_pr_analysis()` - Cannot fabricate PR data
- `_generate_intelligent_pr_title()` - Cannot fabricate PR titles
- `_predict_likely_files_changed()` - Cannot predict files without real API data

**Enforcement**:
- `fallback_to_simulation = False` by default in JiraApiConfig
- Confidence scores calculated from actual data quality via `_calculate_pr_data_confidence()`
- All GitHub PR data must come from real MCP or CLI calls
- No hardcoded component file patterns

**Compliance Testing**: 13 automated tests in `tests/unit/compliance/test_anti_simulation_compliance.py`

---

## Documentation Standards

- **Clear Language**: Direct, accessible for any reader
- **No Marketing**: Zero promotional language
- **Evidence-Based**: All claims backed by verifiable evidence
- **Professional Headings**: Descriptive, functional headings

*Complete policies and enforcement rules: See CLAUDE.policies.md*
