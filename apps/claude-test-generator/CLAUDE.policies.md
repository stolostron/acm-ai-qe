# Test Generator - Policies and Enforcement

## Mandatory Test Plan Generation Policy

**REQUIREMENT**: ALL test plan generation requests MUST trigger comprehensive analysis with universal technology support.

**Mandatory Behavior**:
- ✅ Execute complete 4-agent framework analysis
- ✅ Use real JIRA data, real environment data, real repository data
- ✅ Apply Technology Classification Service for bias-free analysis
- ✅ Perform fresh analysis (no cached/simulated shortcuts)
- ❌ NEVER use simulated data, cached results, or framework shortcuts
- ❌ NEVER generate test plans without comprehensive analysis

---

## Evidence-Based Operation Policy

**REQUIREMENT**: Framework must operate on real data only - no simulation fallbacks permitted.

**Standards**:
- JIRA Data Failures: Framework stops completely with actionable suggestions
- Environment Failures: Framework continues with no-environment context
- No Fake Data: No hardcoded responses, synthetic clusters, or fictional tickets
- Technology Agnostic: Real data collection for any technology ecosystem
- Explicit Error Messages: Clear guidance on failures with resolution steps

**Anti-Simulation Enforcement**:
- `fallback_to_simulation = False` is the default in JiraApiConfig
- Deprecated methods raise `RuntimeError` when called:
  - `_generate_intelligent_pr_analysis()` - Data fabrication blocked
  - `_generate_intelligent_pr_title()` - Title fabrication blocked
  - `_predict_likely_files_changed()` - File prediction blocked
- Confidence scores calculated via `_calculate_pr_data_confidence()` based on actual data quality
- No hardcoded component file patterns (ACM-biased patterns removed)

**Blocked**:
- Simulation data generation when real data collection fails
- Hardcoded fallback responses for JIRA, environment, or QE data
- Synthetic cluster information or fictional test data
- Technology-specific hardcoded patterns or biased assumptions
- Calling deprecated simulation methods (raises RuntimeError)

---

## Universal Technology Support Policy

**REQUIREMENT**: Framework MUST support any JIRA ticket across any technology stack without hardcoded biases.

**Implementation**:
- Technology Classification Service: 9+ technology ecosystems with 70%+ pattern coverage
- Hybrid AI + Script Approach: 70% script + 30% AI enhancement
- Pattern Discovery Service: Dynamic CLI, YAML, and test command generation
- Universal Component Analysis: Replaces all hardcoded technology references

**Supported Ecosystems**: Cluster Management, Kubernetes, OpenShift, Cloud Platforms, Database Systems, Networking, Storage, Security Frameworks, Observability, Generic Technologies

---

## Security Template Enforcement Policy

**REQUIREMENT**: Zero-tolerance for environment data exposure in test plans.

**Required Placeholders**:
- Environment URLs: `<CLUSTER_CONSOLE_URL>`, `<CLUSTER_API_URL>`
- Hostnames: `<CLUSTER_HOST>`
- Credentials: `<CLUSTER_ADMIN_USER>`, `<CLUSTER_ADMIN_PASSWORD>`
- Registry URLs: `<INTERNAL_REGISTRY_URL>`

**Enforcement**:
- Multi-layer security (pre-generation, post-generation, final validation)
- Automatic delivery blocking when environment data detected
- Pipe character escaping (&#124;) for markdown table compatibility

**Prohibited**:
- Real cluster URLs
- Real API endpoints
- Real console URLs
- Real credentials or usernames in CLI commands

---

## Professional Table Format Policy

**REQUIREMENT**: All test cases must use 5-column table format.

**Format**: Step | Action | UI Method | CLI Method | Expected Result

**Required**:
- Separate UI Method and CLI Method columns
- Inline YAML format for table compatibility
- Expected output examples for data retrieval commands
- Pipe character escaping for CLI commands

**Blocked**:
- 4-column or combined Sample Commands format
- Multi-line YAML blocks that break table structure
- Unescaped pipe characters in CLI commands

---

## E2E-Only Enforcement Policy

**REQUIREMENT**: Test plans MUST contain ONLY E2E test scenarios.

**Allowed**:
- End-to-end workflow testing through UI and CLI
- Feature functionality validation
- User scenario testing with real workflows
- Error handling within E2E flows
- Security validation within E2E workflows

**Blocked Test Types**:
- Unit Testing
- Integration Testing
- Performance Testing
- Foundation/Infrastructure Testing
- Component/API Analysis Testing
- Smoke/Sanity Testing

**Enforcement**: Phase 4 integration validates before completion. Non-compliant plans blocked from delivery.

---

## Template-Driven Generation Policy

**REQUIREMENT**: Zero tolerance for inconsistent output.

**Content Validation**:
- Pattern Detection: 14 forbidden patterns with automatic blocking
- Business Context: Mandatory "What We're Doing:" explanations
- Concrete Expectations: Zero tolerance for vague language
- Environment Handling: Systematic placeholders vs specifics

**Quality Gates**:
- 85+ threshold for delivery readiness
- Automatic delivery blocking for critical violations
- Automatic vague language replacement
- Business context required for all test steps

**Forbidden Patterns**:
- "Based on role configuration" (vague expectations)
- Performance/stress/load testing references
- Environment-specific details without placeholders
- HTML tags (`<br/>`, `<div>`, etc.)

---

## Test Case Documentation Standards

**Step Format Requirements**:
- Every step MUST include "What We're Doing:" explanation
- 2-3 lines maximum for readability
- Focus on conceptual understanding, not technical details
- Use simple, clear language

**Repository Reference Standards**:
- ALWAYS provide full GitHub URLs for file references
- NEVER use relative paths
- Include repository name and branch reference
- Provide clickable links for easy access

**10-Step Limit**:
- Maximum 10 steps per test case
- Automatic splitting when limit exceeded
- Each split test case validates complete functionality area

---

## Execution Evidence Policy

**REQUIREMENT**: Zero tolerance for fictional execution claims.

**Required Evidence Pattern**:
```bash
pwd                           # Show working directory
ls -la runs/*/latest/         # Show timestamps BEFORE
[actual command execution]    # Show real command
ls -la [new files]           # Show timestamps AFTER
```

**Blocked**:
- "Fresh execution" claims without command evidence
- Fictional data generation when execution fails
- "Constructed" or "simulated" execution results
- File content claims without timestamp verification

---

## Citation Enforcement

**REQUIREMENT**: Every factual claim in complete reports MUST include verified citations.

**Citation Formats**:
- JIRA: `[JIRA:ACM-XXXXX:status:last_updated]`
- GitHub: `[GitHub:org/repo#PR:state:commit_sha]`
- Documentation: `[Docs:URL#section:last_verified]`
- Code: `[Code:file_path:lines:commit_sha]`

**Scope**:
- Complete Reports: Citations mandatory in detailed analysis sections
- Test Tables: Clean format maintained - NO citations in summary tables

---

## Run Organization Policy

**REQUIREMENT**: Single consolidated directory enforcement.

**Structure**: `runs/ACM-XXXXX/ACM-XXXXX-timestamp/`

**Required**:
- ALL agent outputs saved to ONE main run directory
- Latest symlinks for each ticket
- Automatic ticket-based organization

**Final Deliverables Only**:
- Test-Cases.md
- Complete-Analysis.md
- run-metadata.json

**Blocked**:
- Separate agent directories
- Intermediate files remaining after completion
- Multiple directories per run

---

## Framework Execution Integrity

**7-Layer Safety System**:
1. Execution Uniqueness: Only one framework execution per JIRA ticket
2. Agent Output Validation: Completed agents must have actual output files
3. Data Pipeline Integrity: Phase 4 requires validated agent intelligence
4. Cross-Execution Consistency: 1:1 correspondence between claims and reality
5. Context Architecture Validation: Real context data for inheritance
6. Evidence Validation: Every test element traces to real sources
7. Framework State Monitoring: 95% integrity threshold with fail-fast

**Blocked**:
- Concurrent framework executions for same ticket
- Agent completion claims without output files
- Pattern Extension proceeding without agent intelligence
- Framework proceeding with integrity below 95%

---

## Data Flow Architecture Enforcement

**REQUIREMENT**: All executions MUST use Data Flow Architecture preventing Phase 2.5 bottleneck.

**Required**:
- Parallel data staging: Agent intelligence flows directly to Phase 3
- 100% Agent Intelligence Preservation (prevents 97% data loss)
- Parallel QE Intelligence execution without blocking
- Complete context + QE insights processing in Phase 3

**Blocked**:
- Phase 2.5 synthesis-only approach
- Blocking core data flow for QE analysis
- Agent intelligence truncation or summarization

---

## Credential Exposure Prevention

**REQUIREMENT**: Zero-tolerance credential exposure.

**Enforcement**:
- 11+ credential pattern detection with auto-sanitization
- Real-time detection and blocking
- Automatic replacement with secure placeholders
- Delivery blocking for security violations

**Protected Patterns**:
- Passwords in commands: `-p actualpassword` → `-p <CLUSTER_ADMIN_PASSWORD>`
- Environment URLs: Real domains → `<CLUSTER_CONSOLE_URL>`
- Credential combinations: `user/password` → placeholders

---

## Comprehensive Analysis Guarantee

**REQUIREMENT**: Every test plan request triggers comprehensive analysis.

**Protections**:
- Zero Shortcuts: Prevents framework optimizations that skip steps
- Fresh Analysis: Complete analysis for every request
- Context Isolation: Prevents contamination from previous runs
- Agent Enforcement: All 4 agents perform fresh analysis
- Environment Validation: Real assessment mandatory

**Trigger Patterns**: "generate test plan", "test plan for ACM-XXXXX", "create test cases", JIRA ticket with generation intent

---

## MCP Performance Policy

**REQUIREMENT**: Intelligent MCP integration with fallback guarantee.

**Architecture**:
- Performance When Available: 45-60% GitHub improvement, 25-35% filesystem enhancement
- Seamless Fallback: Automatic degradation to CLI+WebFetch
- Zero Framework Dependency: 100% functionality regardless of MCP status

**Blocked**:
- Framework failure when MCP servers show "failed" status
- Treating MCP as mandatory dependency
- Operations that fail instead of degrading gracefully

---

## Cleanup Policy

**REQUIREMENT**: Zero tolerance for persistent temporary data.

**Phase 0 Cleanup**:
- Remove stale temp_repos/ directory
- Remove framework-level cache/staging directories
- Clean previous execution temporary data

**Phase 5 Cleanup**:
- Remove ALL agent intermediate files
- Remove ALL metadata files
- Remove ALL enforcement directories
- PRESERVE ONLY: Test-Cases.md + Complete-Analysis.md

---

## Complete Analysis Report Structure

**REQUIRED 4-Section Structure**:
1. Summary (with clickable JIRA link and validation status)
2. JIRA Analysis
3. Environment Assessment
4. Implementation Analysis
5. Test Scenarios Analysis

**Required**:
- Clickable links for ALL JIRA, PR, and environment references
- Full JIRA ticket title as clickable link
- Clear feature validation status (✅/❌)

**Blocked**:
- "Executive" in any section heading
- Non-clickable references
- Old sections: Documentation Analysis, QE Intelligence, Feature Deployment, Business Impact

---

## Framework Self-Containment

**All Required Dependencies Included**:
- AI Investigation Services (internal)
- AI Environment Services (internal)
- AI Validation Services (internal)
- Framework Templates and Workflows (internal)
- No external dependencies outside this directory

---

## Compliance Test Suite

**Location**: `tests/unit/compliance/test_anti_simulation_compliance.py`

**Test Coverage** (13 tests):

| Test Category | Tests |
|---------------|-------|
| **Anti-Simulation Compliance** | `test_no_simulation_fallback_enabled`, `test_generate_intelligent_pr_analysis_deprecated`, `test_generate_intelligent_pr_title_deprecated`, `test_predict_likely_files_changed_deprecated`, `test_confidence_calculation_method_exists`, `test_no_hardcoded_confidence_scores` |
| **Universal Technology Support** | `test_technology_classifier_exists`, `test_non_acm_technology_classification` |
| **Configuration Compliance** | `test_json_configs_valid`, `test_active_hooks_json_valid`, `test_mandatory_analysis_config_valid` |
| **Import Compliance** | `test_ai_agent_orchestrator_export`, `test_core_module_imports` |

**Running Tests**:
```bash
python3 -m pytest tests/unit/compliance/test_anti_simulation_compliance.py -v
```

**All tests must pass before any release.**
