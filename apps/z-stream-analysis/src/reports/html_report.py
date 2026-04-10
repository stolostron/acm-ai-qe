#!/usr/bin/env python3
"""
HTML Report Generator for Z-Stream Analysis.

Generates a self-contained interactive HTML report from pipeline run data.
Schema: src/schemas/html_report_schema.json

Usage:
    from src.reports.html_report import generate_html_report
    path = generate_html_report(Path("runs/job_20260331_184305"))
"""

import json
import html as html_mod
import logging
import os
import re as re_mod
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CLS_COLORS = {
    "PRODUCT_BUG": "#ef4444",
    "AUTOMATION_BUG": "#f59e0b",
    "INFRASTRUCTURE": "#6366f1",
    "NO_BUG": "#22c55e",
    "MIXED": "#ec4899",
    "UNKNOWN": "#6b7280",
    "FLAKY": "#a855f7",
}


def _map_diagnosis_to_health(diag: dict) -> dict:
    """Map cluster-diagnosis.json fields to the dict shape html_report rendering expects.

    The rendering code (Environment tab) was written for cluster-health.json format.
    This function translates cluster-diagnosis.json fields so the same rendering
    code works without modification. Falls back gracefully for missing fields.
    """
    result = {}

    # Direct passthrough fields (same name in both schemas)
    for key in ('infrastructure_issues', 'baseline_comparison', 'classification_guidance',
                'operator_health', 'cluster_identity', 'console_plugins',
                'environment_health_score', 'overall_verdict',
                'critical_issue_count', 'warning_issue_count'):
        if key in diag:
            result[key] = diag[key]

    # subsystem_health: map root_cause→root_issue, lowercase→uppercase status,
    # compute components_checked/components_healthy from component lists
    if 'subsystem_health' in diag:
        mapped_subsystems = {}
        for name, data in diag['subsystem_health'].items():
            status_raw = data.get('status', 'unknown')
            mapped_subsystems[name] = {
                'status': status_raw.upper() if isinstance(status_raw, str) else status_raw,
                'root_issue': data.get('root_cause', ''),
                'components_checked': len(data.get('affected_components', [])) + len(data.get('healthy_components', [])),
                'components_healthy': len(data.get('healthy_components', [])),
                'details': data.get('evidence_detail', ''),
                'evidence_tier': data.get('evidence_tier'),
                'log_patterns_detected': data.get('log_patterns_detected', []),
                'traps_triggered': data.get('traps_triggered', []),
            }
        result['subsystem_health'] = mapped_subsystems

    # managed_cluster_detail → managed_cluster_health format
    if 'managed_cluster_detail' in diag:
        mapped_mc = {}
        for name, data in diag['managed_cluster_detail'].items():
            unavail_addons = data.get('addons_unavailable', [])
            mapped_mc[name] = {
                'available': data.get('available', False),
                'joined': data.get('available', False),
                'hub_accepted': True,
                'addon_count': len(unavail_addons) if not data.get('available') else 0,
                'addons_healthy': 0 if unavail_addons else 1,
                'conditions': data.get('condition_message', ''),
                'lease_stale': data.get('lease_stale', False),
            }
        result['managed_cluster_health'] = mapped_mc

    # console_plugin_status → enrich console_plugins if not already provided
    if 'console_plugins' not in result and 'console_plugin_status' in diag:
        result['console_plugins'] = [
            {'name': p.get('name', ''), 'service': p.get('backend_service', ''), 'namespace': p.get('namespace', '')}
            for p in diag['console_plugin_status']
        ]

    return result


def esc(s):
    return html_mod.escape(str(s)) if s else ""


def _find_trace_file(run_dir: Path) -> Optional[Path]:
    """Find the most relevant agent trace file for this run.

    Searches .claude/traces/ for JSONL files whose timestamps overlap with
    the run's pipeline.log.jsonl timestamps. Falls back to the most recent
    trace file if no overlap is found.
    """
    traces_dir = run_dir.parent.parent / ".claude" / "traces"
    if not traces_dir.exists():
        return None

    trace_files = sorted(traces_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not trace_files:
        return None

    # Try to find the trace that was active during this run's time window
    log_file = run_dir / "pipeline.log.jsonl"
    if log_file.exists():
        run_start = log_file.stat().st_mtime - 600  # 10 min before first log
        run_end = log_file.stat().st_mtime + 60
        for tf in trace_files:
            if tf.stat().st_mtime >= run_start and tf.stat().st_ctime <= run_end:
                return tf

    # Fall back to most recent trace
    return trace_files[0] if trace_files else None


def _extract_build_label(jenkins_url: str) -> str:
    """Extract 'job-name / pipeline #N' from a Jenkins URL."""
    # e.g. .../job/qe-acm-automation-poc/job/clc-e2e-pipeline/3932/
    parts = jenkins_url.rstrip("/").split("/")
    build_num = ""
    job_parts = []
    for i, p in enumerate(parts):
        if p == "job" and i + 1 < len(parts):
            job_parts.append(parts[i + 1])
        elif p.isdigit() and job_parts:
            build_num = p
    if job_parts:
        return f"{' / '.join(job_parts)} #{build_num}" if build_num else " / ".join(job_parts)
    return jenkins_url


def load_data(run_dir: Path, trace_file: Optional[Path] = None):
    with open(run_dir / "analysis-results.json") as f:
        analysis = json.load(f)
    logs = []
    log_path = run_dir / "pipeline.log.jsonl"
    if log_path.exists():
        with open(log_path) as f:
            logs = [json.loads(l) for l in f if l.strip()]
    env_status = {}
    env_path = run_dir / "environment-status.json"
    if env_path.exists():
        with open(env_path) as f:
            env_status = json.load(f)
    core_data = {}
    core_path = run_dir / "core-data.json"
    if core_path.exists():
        with open(core_path) as f:
            core_data = json.load(f)
    # v4.0: Load cluster-diagnosis.json for rich environment data
    # Falls back to cluster-health.json for older runs (v3.7-v3.9)
    cluster_health_full = {}
    cd_path = run_dir / "cluster-diagnosis.json"
    ch_path = run_dir / "cluster-health.json"
    if cd_path.exists():
        with open(cd_path) as f:
            cd_raw = json.load(f)
            diag = cd_raw.get("cluster_diagnosis", cd_raw)
            # Warn if structured health fields are missing from diagnosis
            _expected = ['environment_health_score', 'cluster_identity', 'operator_health',
                         'cluster_connectivity', 'critical_issue_count', 'console_plugins']
            _missing = [f for f in _expected if f not in diag]
            if _missing:
                import logging
                logging.getLogger(__name__).warning(
                    f"cluster-diagnosis.json missing structured fields: {_missing}. "
                    f"Environment tab may show incomplete data. "
                    f"Ensure cluster-diagnostic agent Step 6.2a is producing all required fields."
                )
            cluster_health_full = _map_diagnosis_to_health(diag)
    elif ch_path.exists():
        with open(ch_path) as f:
            ch_raw = json.load(f)
            cluster_health_full = ch_raw.get("cluster_health", ch_raw)
    core_data["_cluster_health_full"] = cluster_health_full
    trace = []
    if trace_file is None:
        trace_file = _find_trace_file(run_dir)
    if trace_file and trace_file.exists():
        with open(trace_file) as f:
            trace = [json.loads(l) for l in f if l.strip()]
    return analysis, logs, env_status, core_data, trace


def fmt_ts(ts):
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%H:%M:%S.%f")[:-3]
    except Exception:
        return ts[:12]


def build_test_card(t, idx):
    cls = t.get("classification", "UNKNOWN")
    color = CLS_COLORS.get(cls, "#6b7280")
    conf = t.get("confidence", 0)
    name = esc(t.get("test_name", "Unknown"))
    fa = esc(t.get("feature_area", "Unknown"))
    fmc = esc(t.get("failure_mode_category", ""))
    path = esc(t.get("classification_path", ""))
    root = esc(t.get("root_cause", ""))
    rc_layer = t.get("root_cause_layer")
    rc_layer_name = esc(t.get("root_cause_layer_name", ""))
    cause_owner = esc(t.get("cause_owner", ""))
    inv_steps = t.get("investigation_steps_taken", [])
    cascade = t.get("is_cascading_hook_failure", False)
    blank = t.get("blank_page_detected", False)

    reasoning = t.get("reasoning", {})
    if isinstance(reasoning, str):
        r_summary = esc(reasoning)
        r_conclusion = ""
        r_evidence = []
    else:
        r_summary = esc(reasoning.get("summary", ""))
        r_conclusion = esc(reasoning.get("conclusion", ""))
        r_evidence = reasoning.get("evidence", [])
    evidence_sources = t.get("evidence_sources", [])
    ruled_out = t.get("ruled_out_alternatives", [])
    fix = t.get("recommended_fix", {})

    badges = ""
    if cascade:
        badges += '<span class="badge badge-cascade">Hook Cascade</span>'
    if blank:
        badges += '<span class="badge badge-blank">Blank Page</span>'
    if rc_layer:
        badges += f'<span class="badge badge-layer">L{rc_layer}: {rc_layer_name}</span>'

    evidence_html = ""
    for e in evidence_sources:
        if isinstance(e, str):
            evidence_html += f'<div class="evidence-item tier-2">{esc(e)}</div>'
        else:
            tier = e.get("tier", "?")
            evidence_html += (
                f'<div class="evidence-item tier-{tier}">'
                f'<span class="tier-badge">T{tier}</span>'
                f'{esc(e.get("source", ""))}: {esc(e.get("finding", ""))}'
                f'</div>'
            )

    ruled_html = ""
    for r in ruled_out:
        if isinstance(r, str):
            ruled_html += f'<div class="ruled-out-item">{esc(r)}</div>'
        else:
            ruled_html += (
                f'<div class="ruled-out-item">'
                f'<strong>{esc(r.get("classification", ""))}</strong>: '
                f'{esc(r.get("reason", ""))}</div>'
            )

    fix_html = ""
    if fix:
        if isinstance(fix, str):
            fix_html = f'<div class="fix-section"><div class="fix-action">{esc(fix)}</div></div>'
        else:
            fix_html = f'<div class="fix-section"><div class="fix-action">{esc(fix.get("action", ""))}</div>'
            for step in fix.get("steps", []):
                fix_html += f'<div class="fix-step">{esc(step)}</div>'
            fix_html += f'<div class="fix-owner">Owner: {esc(fix.get("owner", ""))}</div></div>'

    reasoning_ev = "".join(
        f"<li>{esc(r if isinstance(r, str) else json.dumps(r))}</li>" for r in r_evidence
    )

    return f'''
    <div class="test-card" data-classification="{cls}" data-area="{fa}" id="test-{idx}">
      <div class="test-header" onclick="toggleTest({idx})">
        <div class="test-header-left">
          <span class="cls-badge" style="background:{color}">{cls}</span>
          <span class="test-name">{name}</span>
          {badges}
        </div>
        <div class="test-header-right">
          <span class="confidence-badge">{int(conf * 100)}%</span>
          <span class="path-badge">Path {path}</span>
          <span class="chevron" id="chev-{idx}">&#9654;</span>
        </div>
      </div>
      <div class="test-body" id="tbody-{idx}">
        <div class="test-meta-row">
          <span class="meta-tag">Feature: {fa}</span>
          <span class="meta-tag">Failure Mode: {fmc}</span>
        </div>
        <div class="section-label">Root Cause</div>
        <div class="root-cause">{root}</div>
        {f'<div class="cause-owner-line">Caused by: {cause_owner}</div>' if cause_owner else ''}
        {f'<div class="section-label">Investigation Steps</div><ul class="inv-steps">{"".join(f"<li>{esc(s)}</li>" for s in inv_steps)}</ul>' if inv_steps else ''}
        <div class="section-label">Analysis</div>
        <div class="reasoning-text">{r_summary}</div>
        <div class="section-label">Evidence ({len(evidence_sources)} sources)</div>
        <div class="evidence-list">{evidence_html}</div>
        <div class="section-label">Reasoning Evidence</div>
        <ul class="reasoning-evidence">{reasoning_ev}</ul>
        <div class="section-label">Conclusion</div>
        <div class="conclusion-text">{r_conclusion}</div>
        <div class="section-label">Ruled Out</div>
        <div class="ruled-out-list">{ruled_html}</div>
        <div class="section-label">Recommended Fix</div>
        {fix_html}
      </div>
    </div>'''


def build_log_entries(entries):
    rows = ""
    for e in entries:
        level = e.get("level", "info")
        ts = fmt_ts(e.get("timestamp", ""))
        logger = esc(e.get("logger", ""))
        msg = esc(e.get("message", ""))
        rows += (
            f'<div class="log-entry log-{level}">'
            f'<span class="log-ts">{ts}</span>'
            f'<span class="log-level">{level.upper()}</span>'
            f'<span class="log-logger">{logger}</span>'
            f'<span class="log-msg">{msg}</span>'
            f'</div>'
        )
    return rows


def _summarize_trace_output(output_str):
    """Extract a readable summary from tool_result output (JSON string)."""
    if not output_str:
        return ""
    text = str(output_str)
    # The hook stores output as a JSON-encoded string containing stdout/stderr.
    # Try to parse and extract the stdout portion for display.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "stdout" in parsed:
            stdout = parsed["stdout"]
            # Strip ANSI codes
            stdout = re_mod.sub(r'\x1b\[[0-9;]*m', '', stdout)
            return stdout[:300]
        return text[:300]
    except (json.JSONDecodeError, TypeError):
        return text[:300]


def build_trace_entries(trace, run_start_ts=None):
    """Build HTML rows for trace entries.

    Args:
        trace: List of trace event dicts
        run_start_ts: ISO timestamp string. Only include entries at or after
                      this time. If None, include all entries.
    """
    rows = ""
    for e in trace:
        # Filter out entries from before the run started
        if run_start_ts:
            entry_ts = e.get("timestamp", "")
            if entry_ts and entry_ts < run_start_ts:
                continue
        event = e.get("event", "")
        tool = e.get("tool", "")
        ts = fmt_ts(e.get("timestamp", ""))
        mcp = e.get("mcp_server", "")
        mcp_tool = e.get("mcp_tool", "")
        inp = e.get("input", "")
        output = e.get("output", "")
        prompt_text = e.get("prompt", "")
        is_continuation = e.get("is_continuation", False)

        detail = ""

        if event == "tool_call":
            # Show input details for tool calls
            if isinstance(inp, dict):
                if "command" in inp:
                    detail = esc(str(inp["command"])[:300])
                elif "file_path" in inp:
                    detail = esc(inp["file_path"])
                elif "pattern" in inp:
                    detail = f'pattern: {esc(inp["pattern"])}'
                elif "description" in inp:
                    detail = esc(str(inp.get("description", "")))
                else:
                    detail = esc(json.dumps(inp)[:300])
            elif inp:
                detail = esc(str(inp)[:300])

        elif event == "tool_result":
            # Show output for tool results — this was previously missing
            detail = esc(_summarize_trace_output(output))

        elif event == "tool_error":
            detail = esc(str(e.get("error", ""))[:300])

        elif event == "prompt":
            if prompt_text:
                detail = esc(str(prompt_text)[:300])
            elif is_continuation:
                detail = '<span style="color:var(--text-muted);font-style:italic">agent continuation (auto-prompt)</span>'
            else:
                detail = '<span style="color:var(--text-muted);font-style:italic">agent continuation (auto-prompt)</span>'

        elif event == "subagent_complete":
            agent_type = e.get("agent_type", "")
            detail = f'agent_type={esc(agent_type)}'

        elif event == "turn_complete":
            detail = '<span style="color:var(--text-muted)">--- turn boundary ---</span>'

        if mcp:
            tool = f"{mcp}__{mcp_tool}"

        event_cls = (
            "trace-call" if event == "tool_call"
            else "trace-result" if event == "tool_result"
            else "trace-prompt" if event == "prompt"
            else "trace-other"
        )
        rows += (
            f'<div class="log-entry {event_cls}">'
            f'<span class="log-ts">{ts}</span>'
            f'<span class="trace-event">{event}</span>'
            f'<span class="trace-tool">{esc(tool)}</span>'
            f'<span class="log-msg">{detail}</span>'
            f'</div>'
        )
    return rows


def generate_html_report(run_dir: Path, trace_file: Optional[Path] = None) -> Path:
    """Generate the interactive HTML analysis report for a run.

    Args:
        run_dir: Path to the run directory containing analysis-results.json etc.
        trace_file: Optional explicit path to agent trace JSONL. Auto-discovered if None.

    Returns:
        Path to the generated analysis-report.html file.
    """
    run_dir = Path(run_dir)
    analysis, logs, env_status, core_data, trace = load_data(run_dir, trace_file)

    meta = analysis.get("analysis_metadata", {})
    summary = analysis.get("summary", {})
    tests = analysis.get("per_test_analysis", [])
    action_items = analysis.get("action_items", [])
    by_class = summary.get("by_classification", {})

    # Group by feature area
    by_area = {}
    for t in tests:
        fa = t.get("feature_area", "Unknown")
        by_area.setdefault(fa, []).append(t)

    # Group logs by stage
    logs_by_stage = {}
    for l in logs:
        s = l.get("stage", "unknown")
        logs_by_stage.setdefault(s, []).append(l)

    # Build test cards (with per-test error isolation)
    test_card_parts = []
    for i, t in enumerate(tests):
        try:
            test_card_parts.append(build_test_card(t, i))
        except Exception as card_err:
            logger.warning(f"Failed to build card for test {i} ({t.get('test_name', '?')[:60]}): {card_err}")
            test_card_parts.append(
                f'<div class="test-card" id="test-{i}"><div class="test-header">'
                f'<span class="cls-badge" style="background:#6b7280">ERROR</span>'
                f'<span class="test-name">{esc(t.get("test_name", "Unknown"))}</span>'
                f'<span style="color:var(--danger);font-size:12px">Report rendering error: {esc(str(card_err))}</span>'
                f'</div></div>'
            )
    test_cards = "".join(test_card_parts)

    # Build classification filter buttons
    cls_filter_btns = ""
    for k, v in sorted(by_class.items(), key=lambda x: -x[1]):
        if v > 0:
            color = CLS_COLORS.get(k, "#6b7280")
            cls_filter_btns += (
                f'<button class="filter-btn" style="border-color:{color}" '
                f"onclick=\"filterClass('{k}')\">{k} {v}</button>"
            )

    # Build feature area tabs
    area_tabs = ""
    for area_name in sorted(by_area.keys()):
        n = len(by_area[area_name])
        area_tabs += (
            f'<button class="area-tab" data-area="{esc(area_name)}" '
            f"onclick=\"filterArea('{esc(area_name)}')\">"
            f'{esc(area_name)} <span class="area-count">{n}</span></button>'
        )

    # Build log sections
    gather_logs = build_log_entries(logs_by_stage.get("gather", []))
    oracle_logs = build_log_entries(logs_by_stage.get("oracle", []))
    report_logs = build_log_entries(logs_by_stage.get("report", []))
    # Filter trace entries to only include those from the analysis run
    run_start_ts = meta.get("gathered_at", "")
    trace_rows = build_trace_entries(trace, run_start_ts=run_start_ts)
    # Count filtered entries (not total trace entries)
    filtered_trace = [e for e in trace if not run_start_ts or e.get("timestamp", "") >= run_start_ts]

    gather_count = len(logs_by_stage.get("gather", []))
    oracle_count = len(logs_by_stage.get("oracle", []))
    report_count = len(logs_by_stage.get("report", []))
    trace_count = len(filtered_trace)

    # Chart data
    chart_data = json.dumps([
        {"label": k, "value": v, "color": CLS_COLORS.get(k, "#6b7280")}
        for k, v in by_class.items() if v > 0
    ])

    # Action items — collect fix steps from matching tests
    action_html = ""
    for ai_idx, item in enumerate(action_items):
        p = item.get("priority", 0)
        cls = item.get("type", "")
        color = CLS_COLORS.get(cls, "#6b7280")
        action_text = item.get("action", "")
        action_detail = item.get("details", "")

        # Find tests related to this action item and collect their fix steps
        affected_tests = []
        fix_steps_set = []
        for t in tests:
            t_fix = t.get("recommended_fix", {})
            t_root = t.get("root_cause", "")
            # Match by overlapping keywords between action and root cause/fix
            if t_fix and t.get("classification") == cls:
                fix_action = t_fix.get("action", "") if isinstance(t_fix, dict) else str(t_fix)
                # Check if this test's fix is related to the action item
                action_words = set(action_text.lower().split())
                fix_words = set(fix_action.lower().split())
                root_words = set(t_root.lower().split())
                overlap = len(action_words & (fix_words | root_words))
                if overlap >= 2:
                    affected_tests.append(t)
                    if isinstance(t_fix, dict):
                        for step in t_fix.get("steps", []):
                            if step not in fix_steps_set:
                                fix_steps_set.append(step)

        # Build expandable fix detail
        fix_detail_html = ""
        if fix_steps_set or affected_tests:
            steps_html = "".join(
                f'<div class="fix-step">{esc(s)}</div>' for s in fix_steps_set[:8]
            )
            affected_html = "".join(
                f'<div style="font-size:12px;color:var(--text-dim);padding:2px 0">'
                f'&bull; {esc(t.get("test_name", "")[:80])}</div>'
                for t in affected_tests[:6]
            )
            if len(affected_tests) > 6:
                affected_html += f'<div style="font-size:12px;color:var(--text-muted)">...and {len(affected_tests) - 6} more</div>'

            fix_detail_html = f'''
            <div class="action-expand" id="action-body-{ai_idx}">
              {'<div class="section-label">Fix Steps</div>' + steps_html if steps_html else ""}
              {'<div class="section-label" style="margin-top:12px">Affected Tests</div>' + affected_html if affected_html else ""}
            </div>'''

        action_html += f'''
        <div class="action-item" onclick="toggleAction({ai_idx})" style="cursor:pointer;flex-wrap:wrap;">
          <div class="action-priority">P{p}</div>
          <div class="action-body">
            <div class="action-text">{esc(action_text)}</div>
            <div class="action-detail">{esc(action_detail)}</div>
          </div>
          <span class="cls-badge-sm" style="background:{color}">{cls}</span>
          <span class="action-owner">{esc(item.get("owner", ""))}</span>
          <span class="chevron" id="action-chev-{ai_idx}" style="margin-left:4px">&#9654;</span>
          {fix_detail_html}
        </div>'''

    # Environment — combine environment-status.json (base connectivity)
    # with core-data.json's cluster_oracle and cluster_landscape (real health)
    def env_class(val):
        if isinstance(val, bool):
            return "healthy" if val else "down"
        if isinstance(val, (int, float)):
            return "healthy" if val >= 0.7 else "degraded" if val >= 0.4 else "down"
        return ""

    def status_class(status):
        s = str(status).lower()
        if s in ("healthy", "running", "ready", "true", "succeeded"):
            return "healthy"
        if s in ("degraded", "unknown", "pending"):
            return "degraded"
        return "down"

    # v4.0: Read health data from cluster-diagnosis.json (via _cluster_health_full),
    # then cluster_health in core-data.json, then environment-status.json
    cluster_health_data = core_data.get("cluster_health", {})
    ch_full = core_data.get("_cluster_health_full", {})
    environment_data = core_data.get("environment", {})

    # Base scores: prefer cluster-diagnosis.json (ch_full), then core-data cluster_health,
    # then environment key, then env_status file
    if ch_full.get("environment_health_score") is not None:
        env_score_base = ch_full["environment_health_score"]
        cluster_conn = ch_full.get("cluster_connectivity", True)
        api_acc = True
    elif cluster_health_data.get("environment_health_score") is not None:
        env_score_base = cluster_health_data["environment_health_score"]
        cluster_conn = True
        api_acc = True
    elif environment_data.get("environment_score") is not None:
        env_score_base = environment_data.get("environment_score", 0) or 0
        cluster_conn = environment_data.get("cluster_connectivity", False)
        api_acc = True
    else:
        env_score_base = env_status.get("environment_score", 0) or 0
        cluster_conn = env_status.get("cluster_connectivity", False)
        api_acc = env_status.get("api_accessibility", False)
    target_used = env_status.get("target_cluster_used", False) or bool(ch_full) or bool(cluster_health_data)

    # Oracle data from core-data.json (feature context)
    cluster_oracle = core_data.get("cluster_oracle", {})
    cluster_landscape = core_data.get("cluster_landscape", {})
    oracle_feature_health = cluster_oracle.get("overall_feature_health", {})
    oracle_dep_health = cluster_oracle.get("dependency_health", {})
    oracle_score = oracle_feature_health.get("score")
    oracle_signal = oracle_feature_health.get("signal", "")
    blocking_issues = oracle_feature_health.get("blocking_issues", [])

    # Use diagnosis score (v4.0) > cluster health score (v3.7) > oracle score > base
    if ch_full.get("environment_health_score") is not None:
        effective_score = ch_full["environment_health_score"]
    elif cluster_health_data.get("environment_health_score") is not None:
        effective_score = cluster_health_data["environment_health_score"]
    elif oracle_score is not None:
        effective_score = oracle_score
    else:
        effective_score = env_score_base

    # v3.7: Build rich environment sections from cluster-health.json
    ch_full = core_data.get("_cluster_health_full", {})

    # Infrastructure issues from health audit
    infra_issues_html = ""
    for issue in ch_full.get("infrastructure_issues", []):
        sev = issue.get("severity", "INFO")
        sev_color = "var(--danger)" if sev == "CRITICAL" else "var(--warning)" if sev == "WARNING" else "var(--text-dim)"
        infra_issues_html += (
            f'<div class="evidence-item tier-1" style="margin-bottom:6px;border-left:3px solid {sev_color};padding-left:10px">'
            f'<span style="color:{sev_color};font-weight:600;font-size:11px">{esc(sev)}</span> '
            f'<strong>{esc(issue.get("component", ""))}</strong>'
            f'<div style="font-size:12px;margin-top:2px">{esc(issue.get("finding", ""))}</div>'
            f'<div style="font-size:11px;color:var(--text-dim);margin-top:2px">{esc(issue.get("impact", ""))}</div>'
            f'{"<div style=font-size:11px;color:var(--accent);margin-top:2px>Trap: " + esc(issue.get("diagnostic_trap")) + "</div>" if issue.get("diagnostic_trap") else ""}'
            f'</div>'
        )

    # Subsystem health from health audit
    subsystem_html = ""
    for sub_name, sub_data in ch_full.get("subsystem_health", {}).items():
        if not isinstance(sub_data, dict):
            continue
        status = sub_data.get("status", "UNKNOWN")
        checked = sub_data.get("components_checked", 0)
        healthy = sub_data.get("components_healthy", 0)
        root = sub_data.get("root_issue", "")
        s_class = "healthy" if status == "OK" else "degraded" if status == "DEGRADED" else "down"
        subsystem_html += (
            f'<div class="env-item">'
            f'<div class="env-label">{esc(sub_name)}</div>'
            f'<div class="env-value {s_class}">{esc(status)} ({healthy}/{checked})</div>'
            f'{"<div style=font-size:11px;color:var(--text-dim);margin-top:2px>" + esc(root) + "</div>" if root else ""}'
            f'</div>'
        )

    # Operator health from health audit
    ch_operator_html = ""
    for op_name, op_data in ch_full.get("operator_health", {}).items():
        if not isinstance(op_data, dict):
            continue
        status = op_data.get("status", "UNKNOWN")
        desired = op_data.get("desired_replicas", 0)
        available = op_data.get("available_replicas", 0)
        detail = op_data.get("detail", "")
        s_class = "healthy" if status == "OK" else "degraded" if status == "DEGRADED" else "down"
        ch_operator_html += (
            f'<div class="env-item">'
            f'<div class="env-label">{esc(op_name)}</div>'
            f'<div class="env-value {s_class}">{esc(status)} ({available}/{desired})</div>'
            f'{"<div style=font-size:11px;color:var(--text-dim);margin-top:2px>" + esc(detail) + "</div>" if detail else ""}'
            f'</div>'
        )

    # Managed clusters from health audit
    ch_mc_html = ""
    for mc_name, mc_data in ch_full.get("managed_cluster_health", {}).items():
        if not isinstance(mc_data, dict):
            continue
        avail = mc_data.get("available", False)
        addons_h = mc_data.get("addons_healthy", 0)
        addons_t = mc_data.get("addon_count", 0)
        ch_mc_html += (
            f'<div class="env-item">'
            f'<div class="env-label">{esc(mc_name)}</div>'
            f'<div class="env-value {"healthy" if avail else "down"}">{"Ready" if avail else "NotReady"}'
            f' ({addons_h}/{addons_t} addons)</div>'
            f'</div>'
        )

    # Cluster identity from health audit
    ch_identity = ch_full.get("cluster_identity", {})
    identity_html = ""
    if ch_identity:
        identity_html = (
            f'<div class="env-grid">'
            f'<div class="env-item"><div class="env-label">ACM Version</div><div class="env-value healthy">{esc(ch_identity.get("acm_version", ""))}</div></div>'
            f'<div class="env-item"><div class="env-label">OCP Version</div><div class="env-value healthy">{esc(ch_identity.get("ocp_version", ""))}</div></div>'
            f'<div class="env-item"><div class="env-label">MCH Namespace</div><div class="env-value healthy">{esc(ch_identity.get("mch_namespace", ""))}</div></div>'
            f'<div class="env-item"><div class="env-label">Nodes</div><div class="env-value healthy">{ch_identity.get("node_ready_count", 0)}/{ch_identity.get("node_count", 0)} Ready</div></div>'
            f'<div class="env-item"><div class="env-label">Managed Clusters</div><div class="env-value {"healthy" if ch_identity.get("managed_cluster_ready_count", 0) == ch_identity.get("managed_cluster_count", 0) else "degraded"}">{ch_identity.get("managed_cluster_ready_count", 0)}/{ch_identity.get("managed_cluster_count", 0)} Ready</div></div>'
            f'<div class="env-item"><div class="env-label">MCH Phase</div><div class="env-value {"healthy" if ch_identity.get("mch_phase") == "Running" else "down"}">{esc(ch_identity.get("mch_phase", ""))}</div></div>'
            f'</div>'
        )

    # K8s service health — prefer health audit subsystem data, fall back to env_status
    svc_health_html = ""
    if not ch_full:
        for k, v in env_status.get("service_health", {}).items():
            svc_health_html += (
                f'<div class="env-item"><div class="env-label">{esc(k)}</div>'
                f'<div class="env-value {env_class(v)}">{"Healthy" if v else "Unhealthy"}</div></div>'
            )

    ns_html = ""
    if not ch_full:
        for k, v in env_status.get("namespace_access", {}).items():
            ns_html += (
                f'<div class="env-item"><div class="env-label">{esc(k)}</div>'
                f'<div class="env-value {env_class(v)}">{"Accessible" if v else "Denied"}</div></div>'
            )

    # Dependency health from oracle
    dep_health_html = ""
    for dep_id, dep in oracle_dep_health.items():
        if not isinstance(dep, dict):
            continue
        status = dep.get("status", "unknown")
        dep_type = dep.get("type", "")
        detail = dep.get("detail", "")
        dep_health_html += (
            f'<div class="env-item">'
            f'<div class="env-label">{esc(dep.get("name", dep_id))} '
            f'<span style="opacity:0.5">({esc(dep_type)})</span></div>'
            f'<div class="env-value {status_class(status)}">{esc(status.capitalize())}</div>'
            f'<div style="font-size:12px;color:var(--text-dim);margin-top:4px">{esc(detail)}</div>'
            f'</div>'
        )

    # Blocking issues
    blocking_html = ""
    for issue in blocking_issues:
        blocking_html += (
            f'<div class="evidence-item tier-1" style="margin-bottom:4px">'
            f'<span class="tier-badge" style="background:var(--danger)">!</span>'
            f'{esc(issue)}</div>'
        )

    # Managed clusters from landscape or oracle
    managed_clusters = cluster_landscape.get("managed_clusters", [])
    managed_html = ""
    if managed_clusters:
        for mc in managed_clusters:
            name = mc.get("name", "")
            status = mc.get("status", "Unknown")
            avail = mc.get("available", "Unknown")
            managed_html += (
                f'<div class="env-item">'
                f'<div class="env-label">{esc(name)}</div>'
                f'<div class="env-value {status_class(status)}">{esc(status)}</div>'
                f'</div>'
            )
    else:
        # Fall back to oracle detail if landscape doesn't have managed clusters
        mc_dep = oracle_dep_health.get("managed-clusters-status", {})
        if mc_dep:
            raw = mc_dep.get("raw_output", "")
            if raw:
                for line in raw.strip().split("\n"):
                    parts = line.split()
                    if len(parts) >= 2:
                        name, avail = parts[0], parts[1]
                        is_ready = avail.lower() == "true"
                        managed_html += (
                            f'<div class="env-item">'
                            f'<div class="env-label">{esc(name)}</div>'
                            f'<div class="env-value {"healthy" if is_ready else "down"}">'
                            f'{"Ready" if is_ready else "NotReady"}</div>'
                            f'</div>'
                        )

    # Operators from landscape
    operators = cluster_landscape.get("operator_status", [])
    operator_html = ""
    for op in operators:
        name = op.get("name", "")
        status = op.get("status", "Unknown")
        operator_html += (
            f'<div class="env-item">'
            f'<div class="env-label">{esc(name)}</div>'
            f'<div class="env-value {status_class(status)}">{esc(status)}</div>'
            f'</div>'
        )

    # Jenkins URL parts
    jenkins_url_raw = meta.get("jenkins_url", "")
    jenkins_url = esc(jenkins_url_raw)
    build_label = esc(_extract_build_label(jenkins_url_raw))
    build_result = esc(meta.get("build_result", "UNKNOWN"))
    analyzed_at = esc(meta.get("analyzed_at", "")[:10])
    analyzer_ver = esc(meta.get("analyzer_version", "3.9"))
    total_tests = summary.get("total_tests", 0)
    passed = summary.get("passed_count", 0)
    failed = summary.get("total_failures", 0)
    pass_rate = summary.get("pass_rate", 0)
    overall_conf = int(summary.get("overall_confidence", 0) * 100)

    html_out = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Z-Stream Analysis — {build_label}</title>
<style>
:root {{
  --bg: #0f1117; --bg-card: #1a1d27; --bg-card-hover: #1e2130;
  --bg-section: #151822; --border: #2a2d3a; --border-light: #363a4a;
  --text: #e2e4ea; --text-dim: #8b8fa3; --text-muted: #6b6f82;
  --accent: #6366f1; --accent-glow: rgba(99,102,241,0.15);
  --success: #22c55e; --danger: #ef4444; --warning: #f59e0b;
  --radius: 10px; --radius-sm: 6px;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif; line-height: 1.5; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}

.hero {{ background: linear-gradient(135deg, #1a1d2e 0%, #0f1117 100%); border: 1px solid var(--border); border-radius: 16px; padding: 32px; margin-bottom: 24px; }}
.hero-top {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }}
.hero-title {{ font-size: 24px; font-weight: 600; color: #fff; }}
.hero-subtitle {{ font-size: 14px; color: var(--text-dim); margin-top: 4px; }}
.hero-subtitle a {{ color: var(--accent); text-decoration: none; }}
.hero-subtitle a:hover {{ text-decoration: underline; }}
.build-badge {{ background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 20px; text-align: center; }}
.build-result {{ font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
.build-result.unstable {{ color: var(--warning); }}
.build-result.failure {{ color: var(--danger); }}
.build-result.success {{ color: var(--success); }}

.stats-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px; }}
.stat-card {{ background: var(--bg-section); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px; text-align: center; }}
.stat-value {{ font-size: 28px; font-weight: 700; color: #fff; }}
.stat-label {{ font-size: 12px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }}
.stat-value.pass {{ color: var(--success); }}
.stat-value.fail {{ color: var(--danger); }}

.chart-section {{ display: flex; gap: 24px; align-items: center; flex-wrap: wrap; }}
.donut-container {{ position: relative; width: 180px; height: 180px; flex-shrink: 0; }}
.donut-center {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }}
.donut-center-value {{ font-size: 28px; font-weight: 700; color: #fff; }}
.donut-center-label {{ font-size: 11px; color: var(--text-dim); text-transform: uppercase; }}
.legend {{ display: flex; flex-direction: column; gap: 8px; }}
.legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 14px; }}
.legend-dot {{ width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }}
.legend-value {{ font-weight: 600; color: #fff; min-width: 24px; }}

.tabs {{ display: flex; gap: 0; background: var(--bg-section); border: 1px solid var(--border); border-radius: var(--radius) var(--radius) 0 0; overflow-x: auto; }}
.tab {{ padding: 12px 24px; font-size: 14px; font-weight: 500; color: var(--text-dim); cursor: pointer; border: none; background: none; border-bottom: 2px solid transparent; transition: all 0.2s; white-space: nowrap; }}
.tab:hover {{ color: var(--text); background: rgba(255,255,255,0.03); }}
.tab.active {{ color: var(--accent); border-bottom-color: var(--accent); background: rgba(99,102,241,0.05); }}
.tab-panel {{ display: none; border: 1px solid var(--border); border-top: none; border-radius: 0 0 var(--radius) var(--radius); background: var(--bg-card); }}
.tab-panel.active {{ display: block; }}

.section {{ margin-bottom: 24px; }}
.section-title {{ font-size: 18px; font-weight: 600; color: #fff; margin-bottom: 16px; }}

.action-item {{ display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-sm); margin-bottom: 8px; transition: border-color 0.2s; }}
.action-item:hover {{ border-color: var(--border-light); }}
.action-priority {{ background: var(--accent); color: #fff; font-size: 12px; font-weight: 700; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
.action-body {{ flex: 1; min-width: 0; }}
.action-text {{ font-size: 14px; color: var(--text); }}
.action-detail {{ font-size: 12px; color: var(--text-dim); margin-top: 2px; }}
.action-owner {{ font-size: 12px; color: var(--text-muted); white-space: nowrap; }}
.action-expand {{ display: none; width: 100%; padding: 12px 0 0 44px; }}
.action-expand.open {{ display: block; }}

.cls-badge {{ display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; color: #fff; letter-spacing: 0.03em; }}
.cls-badge-sm {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 700; color: #fff; letter-spacing: 0.03em; white-space: nowrap; }}

.test-filters {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }}
.filter-btn {{ padding: 6px 14px; border-radius: 20px; border: 1px solid var(--border); background: var(--bg-section); color: var(--text-dim); font-size: 13px; cursor: pointer; transition: all 0.2s; }}
.filter-btn:hover, .filter-btn.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
.area-tab {{ padding: 6px 14px; border-radius: 20px; border: 1px solid var(--border); background: var(--bg-section); color: var(--text-dim); font-size: 13px; cursor: pointer; transition: all 0.2s; }}
.area-tab:hover, .area-tab.active {{ background: var(--bg-card-hover); border-color: var(--accent); color: var(--text); }}
.area-count {{ background: rgba(255,255,255,0.1); padding: 1px 6px; border-radius: 10px; font-size: 11px; margin-left: 4px; }}
.search-input {{ padding: 8px 14px; border-radius: var(--radius-sm); border: 1px solid var(--border); background: var(--bg-section); color: var(--text); font-size: 13px; width: 240px; outline: none; }}
.search-input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-glow); }}

.test-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-sm); margin-bottom: 6px; transition: border-color 0.2s; }}
.test-card:hover {{ border-color: var(--border-light); }}
.test-header {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; cursor: pointer; gap: 12px; }}
.test-header-left {{ display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }}
.test-header-right {{ display: flex; align-items: center; gap: 10px; flex-shrink: 0; }}
.test-name {{ font-size: 13px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.confidence-badge {{ font-size: 12px; font-weight: 600; color: var(--text); background: var(--bg-section); padding: 2px 8px; border-radius: 4px; }}
.path-badge {{ font-size: 11px; color: var(--text-muted); background: var(--bg); padding: 2px 8px; border-radius: 4px; }}
.chevron {{ color: var(--text-muted); font-size: 11px; transition: transform 0.2s; }}
.chevron.open {{ transform: rotate(90deg); }}
.badge {{ font-size: 10px; padding: 2px 6px; border-radius: 3px; font-weight: 600; }}
.badge-cascade {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
.badge-blank {{ background: rgba(239,68,68,0.15); color: #ef4444; }}
.badge-layer {{ background: rgba(139,92,246,0.15); color: #8b5cf6; }}
.cause-owner-line {{ font-size: 12px; color: var(--text-muted); margin: 4px 0 8px; font-style: italic; }}
.inv-steps {{ font-size: 12px; color: var(--text-dim); padding-left: 20px; margin: 4px 0 12px; }}
.inv-steps li {{ margin: 3px 0; }}

.test-body {{ display: none; padding: 0 16px 16px; border-top: 1px solid var(--border); }}
.test-body.open {{ display: block; }}
.test-meta-row {{ display: flex; gap: 8px; margin: 12px 0; flex-wrap: wrap; }}
.meta-tag {{ font-size: 12px; color: var(--text-dim); background: var(--bg); padding: 3px 10px; border-radius: 4px; }}
.section-label {{ font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin: 14px 0 6px; }}
.root-cause {{ font-size: 13px; color: var(--warning); background: rgba(245,158,11,0.08); padding: 10px 12px; border-radius: var(--radius-sm); border-left: 3px solid var(--warning); }}
.reasoning-text, .conclusion-text {{ font-size: 13px; color: var(--text); padding: 8px 0; }}
.evidence-list {{ display: flex; flex-direction: column; gap: 4px; }}
.evidence-item {{ font-size: 13px; color: var(--text); padding: 8px 10px; background: var(--bg); border-radius: var(--radius-sm); display: flex; align-items: flex-start; gap: 8px; }}
.tier-badge {{ background: var(--accent); color: #fff; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 3px; flex-shrink: 0; }}
.tier-2 .tier-badge {{ background: #f59e0b; }}
.tier-3 .tier-badge {{ background: #6b7280; }}
.reasoning-evidence {{ font-size: 13px; color: var(--text-dim); padding-left: 20px; }}
.reasoning-evidence li {{ margin: 4px 0; }}
.ruled-out-list {{ display: flex; flex-direction: column; gap: 4px; }}
.ruled-out-item {{ font-size: 13px; color: var(--text-dim); padding: 6px 10px; background: var(--bg); border-radius: var(--radius-sm); }}
.fix-section {{ background: rgba(34,197,94,0.06); border: 1px solid rgba(34,197,94,0.15); border-radius: var(--radius-sm); padding: 12px; }}
.fix-action {{ font-size: 14px; font-weight: 600; color: var(--success); margin-bottom: 6px; }}
.fix-step {{ font-size: 13px; color: var(--text); padding: 3px 0 3px 16px; position: relative; }}
.fix-step::before {{ content: "\\2022"; position: absolute; left: 4px; color: var(--text-muted); }}
.fix-owner {{ font-size: 12px; color: var(--text-muted); margin-top: 8px; }}

.log-panel {{ padding: 0; font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace; }}
.log-stage-header {{ padding: 12px 16px; font-size: 14px; font-weight: 600; color: #fff; background: var(--bg-section); border-bottom: 1px solid var(--border); cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
.log-stage-header:hover {{ background: var(--bg-card-hover); }}
.log-stage-body {{ display: none; }}
.log-stage-body.open {{ display: block; max-height: 600px; overflow-y: auto; }}
.log-count {{ font-size: 12px; color: var(--text-muted); font-weight: 400; }}
.log-entry {{ display: flex; gap: 8px; padding: 3px 16px; font-size: 12px; line-height: 1.6; border-bottom: 1px solid rgba(255,255,255,0.02); align-items: flex-start; }}
.log-entry:hover {{ background: rgba(255,255,255,0.02); }}
.log-ts {{ color: var(--text-muted); flex-shrink: 0; width: 90px; }}
.log-level {{ font-weight: 600; flex-shrink: 0; width: 56px; font-size: 11px; }}
.log-debug .log-level {{ color: var(--text-muted); }}
.log-info .log-level {{ color: var(--accent); }}
.log-warning .log-level {{ color: var(--warning); }}
.log-error .log-level {{ color: var(--danger); }}
.log-logger {{ color: var(--text-dim); flex-shrink: 0; width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.log-msg {{ color: var(--text); word-break: break-all; flex: 1; min-width: 0; }}
.trace-event {{ font-weight: 600; flex-shrink: 0; width: 100px; font-size: 11px; }}
.trace-tool {{ color: var(--warning); flex-shrink: 0; width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.trace-call .trace-event {{ color: var(--accent); }}
.trace-result .trace-event {{ color: var(--success); }}
.trace-prompt .trace-event {{ color: var(--warning); }}
.trace-other .trace-event {{ color: var(--text-muted); }}
.trace-result .log-msg {{ color: var(--text-dim); }}

.log-filters {{ display: flex; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--border); background: var(--bg-section); }}
.log-filter {{ padding: 4px 12px; border-radius: 14px; border: 1px solid var(--border); background: var(--bg); color: var(--text-dim); font-size: 12px; cursor: pointer; transition: all 0.2s; }}
.log-filter.active {{ border-color: var(--accent); color: var(--accent); background: var(--accent-glow); }}

.env-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
.env-item {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 12px; }}
.env-label {{ font-size: 12px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.03em; }}
.env-value {{ font-size: 16px; font-weight: 600; color: #fff; margin-top: 4px; }}
.env-value.healthy {{ color: var(--success); }}
.env-value.degraded {{ color: var(--warning); }}
.env-value.down {{ color: var(--danger); }}

::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: var(--bg); }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--border-light); }}

@media (max-width: 768px) {{
  .hero-top {{ flex-direction: column; gap: 16px; }}
  .chart-section {{ flex-direction: column; align-items: flex-start; }}
  .test-header {{ flex-direction: column; align-items: flex-start; gap: 8px; }}
  .test-header-right {{ width: 100%; justify-content: flex-end; }}
  .log-logger {{ display: none; }}
}}
</style>
</head>
<body>
<div class="container">

<div class="hero">
  <div class="hero-top">
    <div>
      <div class="hero-title">Pipeline Failure Analysis</div>
      <div class="hero-subtitle">
        <a href="{jenkins_url}" target="_blank">{build_label}</a>
        &nbsp;&middot;&nbsp; {analyzed_at} &nbsp;&middot;&nbsp; v{analyzer_ver}
      </div>
    </div>
    <div class="build-badge">
      <div class="build-result {build_result.lower()}">{build_result}</div>
    </div>
  </div>

  <div class="stats-row">
    <div class="stat-card"><div class="stat-value">{total_tests}</div><div class="stat-label">Total Tests</div></div>
    <div class="stat-card"><div class="stat-value pass">{passed}</div><div class="stat-label">Passed</div></div>
    <div class="stat-card"><div class="stat-value fail">{failed}</div><div class="stat-label">Failed</div></div>
    <div class="stat-card"><div class="stat-value">{pass_rate:.1f}%</div><div class="stat-label">Pass Rate</div></div>
    <div class="stat-card"><div class="stat-value">{overall_conf}%</div><div class="stat-label">Confidence</div></div>
  </div>

  <div class="chart-section">
    <div class="donut-container">
      <canvas id="donut" width="180" height="180"></canvas>
      <div class="donut-center">
        <div class="donut-center-value">{failed}</div>
        <div class="donut-center-label">Failures</div>
      </div>
    </div>
    <div class="legend" id="legend"></div>
  </div>
</div>

<div class="tabs" id="mainTabs">
  <button class="tab active" onclick="showTab('results', this)">Results</button>
  <button class="tab" onclick="showTab('logs', this)">Pipeline Logs</button>
  <button class="tab" onclick="showTab('environment', this)">Environment</button>
</div>

<!-- Results Tab -->
<div class="tab-panel active" id="panel-results">
  <div style="padding: 24px;">
    <div class="section">
      <div class="section-title">Test Analysis ({len(tests)} failures)</div>
      <div class="test-filters">
        <button class="filter-btn active" onclick="filterClass('ALL')">All {len(tests)}</button>
        {cls_filter_btns}
        <span style="color:var(--text-muted);font-size:12px;margin-left:8px;">Feature:</span>
        <button class="area-tab active" onclick="filterArea('ALL')">All</button>
        {area_tabs}
        <input type="text" class="search-input" placeholder="Search tests..." oninput="searchTests(this.value)" />
      </div>
      <div id="testList">{test_cards}</div>
    </div>
    <div class="section">
      <div class="section-title">Action Items</div>
      {action_html}
    </div>
  </div>
</div>

<!-- Logs Tab -->
<div class="tab-panel" id="panel-logs">
  <div class="log-filters">
    <button class="log-filter active" onclick="filterLogs('all')">All</button>
    <button class="log-filter" onclick="filterLogs('info')">Info</button>
    <button class="log-filter" onclick="filterLogs('warning')">Warning</button>
    <button class="log-filter" onclick="filterLogs('debug')">Debug</button>
  </div>
  <div class="log-panel" id="logPanel">
    <div class="log-stage-header" onclick="toggleLogStage('oracle')">
      Stage 0: Environment Oracle <span class="log-count">{oracle_count} entries <span id="oracle-chev">&#9654;</span></span>
    </div>
    <div class="log-stage-body" id="log-oracle">{oracle_logs}</div>

    <div class="log-stage-header" onclick="toggleLogStage('gather')">
      Stage 1: Data Gathering <span class="log-count">{gather_count} entries <span id="gather-chev">&#9654;</span></span>
    </div>
    <div class="log-stage-body" id="log-gather">{gather_logs}</div>

    <div class="log-stage-header" onclick="toggleLogStage('trace')">
      Stage 2: AI Analysis <span class="log-count">{trace_count} entries <span id="trace-chev">&#9654;</span></span>
    </div>
    <div class="log-stage-body" id="log-trace">{trace_rows}</div>

    <div class="log-stage-header" onclick="toggleLogStage('report')">
      Stage 3: Report Generation <span class="log-count">{report_count} entries <span id="report-chev">&#9654;</span></span>
    </div>
    <div class="log-stage-body" id="log-report">{report_logs}</div>
  </div>
</div>

<!-- Environment Tab -->
<div class="tab-panel" id="panel-environment">
  <div style="padding: 24px;">

    <!-- Overview scores -->
    <div class="section-title">Environment Overview</div>
    <div class="env-grid">
      <div class="env-item">
        <div class="env-label">Feature Health Score</div>
        <div class="env-value {env_class(effective_score)}">{effective_score:.2f}</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:2px">{"Cluster Diagnostic" if ch_full.get("overall_verdict") else ("Health Audit" if cluster_health_data.get("overall_verdict") else ("Oracle: " + oracle_signal if oracle_signal else "Base connectivity only"))}</div>
      </div>
      <div class="env-item">
        <div class="env-label">Base Env Score</div>
        <div class="env-value {env_class(env_score_base)}">{env_score_base:.2f}</div>
        <div style="font-size:11px;color:var(--text-muted);margin-top:2px">K8s control plane</div>
      </div>
      <div class="env-item">
        <div class="env-label">Cluster Connectivity</div>
        <div class="env-value {env_class(cluster_conn)}">{"Connected" if cluster_conn else "Disconnected"}</div>
      </div>
      <div class="env-item">
        <div class="env-label">API Server</div>
        <div class="env-value {env_class(api_acc)}">{"Accessible" if api_acc else "Unavailable"}</div>
      </div>
    </div>

    <!-- Cluster Identity (v3.7) -->
    {"<div style='margin-top:20px'><div class='section-label'>Cluster Identity</div><div style='margin-top:8px'>" + identity_html + "</div></div>" if identity_html else ""}

    <!-- Infrastructure Issues (v3.7) -->
    {"<div style='margin-top:20px'><div class='section-label' style='color:var(--danger)'>Infrastructure Issues (" + str(len(ch_full.get('infrastructure_issues', []))) + ")</div><div style='margin-top:8px'>" + infra_issues_html + "</div></div>" if infra_issues_html else ""}

    <!-- Blocking Issues (from oracle, legacy) -->
    {"<div style='margin-top:20px'><div class='section-label' style='color:var(--danger)'>Blocking Issues</div><div style='margin-top:8px'>" + blocking_html + "</div></div>" if blocking_html and not infra_issues_html else ""}

    <!-- Operator Health (v3.7) -->
    {"<div style='margin-top:20px'><div class='section-label'>Operator Health</div><div class='env-grid' style='margin-top:8px'>" + ch_operator_html + "</div></div>" if ch_operator_html else ("" if not operator_html else "<div style='margin-top:20px'><div class='section-label'>Operators</div><div class='env-grid' style='margin-top:8px'>" + operator_html + "</div></div>")}

    <!-- Subsystem Health (v3.7) -->
    {"<div style='margin-top:20px'><div class='section-label'>Subsystem Health</div><div class='env-grid' style='margin-top:8px'>" + subsystem_html + "</div></div>" if subsystem_html else ""}

    <!-- Managed Clusters -->
    {"<div style='margin-top:20px'><div class='section-label'>Managed Clusters</div><div class='env-grid' style='margin-top:8px'>" + (ch_mc_html or managed_html) + "</div></div>" if (ch_mc_html or managed_html) else ""}

    <!-- Dependency Health (from oracle, shown when no health audit) -->
    {"<div style='margin-top:20px'><div class='section-label'>Dependency Health (Oracle)</div><div class='env-grid' style='margin-top:8px'>" + dep_health_html + "</div></div>" if dep_health_html and not ch_full else ""}

    <!-- K8s Control Plane (legacy, shown when no health audit) -->
    {"<div style='margin-top:20px'><div class='section-label'>K8s Control Plane</div><div class='env-grid' style='margin-top:8px'>" + svc_health_html + "</div></div>" if svc_health_html else ""}

    <!-- Namespace Access (legacy, shown when no health audit) -->
    {"<div style='margin-top:20px'><div class='section-label'>Namespace Access</div><div class='env-grid' style='margin-top:8px'>" + ns_html + "</div></div>" if ns_html else ""}
  </div>
</div>

</div>

<script>
const chartData = {chart_data};

function drawDonut() {{
  const canvas = document.getElementById('donut');
  const ctx = canvas.getContext('2d');
  const cx = 90, cy = 90, outerR = 80, innerR = 52;
  const total = chartData.reduce((s, d) => s + d.value, 0);
  let startAngle = -Math.PI / 2;
  const legend = document.getElementById('legend');
  legend.innerHTML = '';
  chartData.forEach(d => {{
    const sliceAngle = (d.value / total) * 2 * Math.PI;
    ctx.beginPath();
    ctx.arc(cx, cy, outerR, startAngle, startAngle + sliceAngle);
    ctx.arc(cx, cy, innerR, startAngle + sliceAngle, startAngle, true);
    ctx.closePath();
    ctx.fillStyle = d.color;
    ctx.fill();
    startAngle += sliceAngle;
    const li = document.createElement('div');
    li.className = 'legend-item';
    li.innerHTML = '<div class="legend-dot" style="background:' + d.color + '"></div><span class="legend-value">' + d.value + '</span>' + d.label.replace(/_/g, ' ');
    legend.appendChild(li);
  }});
}}
drawDonut();

function showTab(name, btn) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  btn.classList.add('active');
}}

function toggleTest(idx) {{
  document.getElementById('tbody-' + idx).classList.toggle('open');
  document.getElementById('chev-' + idx).classList.toggle('open');
}}

let activeClass = 'ALL', activeArea = 'ALL', searchTerm = '';
function applyFilters() {{
  document.querySelectorAll('.test-card').forEach(card => {{
    const cls = card.dataset.classification;
    const area = card.dataset.area;
    const name = card.querySelector('.test-name').textContent.toLowerCase();
    const ok = (activeClass === 'ALL' || cls === activeClass) &&
               (activeArea === 'ALL' || area === activeArea) &&
               (!searchTerm || name.includes(searchTerm.toLowerCase()));
    card.style.display = ok ? '' : 'none';
  }});
}}
function filterClass(cls) {{
  activeClass = cls;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  applyFilters();
}}
function filterArea(area) {{
  activeArea = area;
  document.querySelectorAll('.area-tab').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  applyFilters();
}}
function searchTests(term) {{ searchTerm = term; applyFilters(); }}

function toggleAction(idx) {{
  const body = document.getElementById('action-body-' + idx);
  const chev = document.getElementById('action-chev-' + idx);
  if (body) {{
    body.classList.toggle('open');
    if (chev) chev.classList.toggle('open');
  }}
}}

function toggleLogStage(stage) {{
  const body = document.getElementById('log-' + stage);
  const chev = document.getElementById(stage + '-chev');
  body.classList.toggle('open');
  if (chev) chev.innerHTML = body.classList.contains('open') ? '&#9660;' : '&#9654;';
}}

function filterLogs(level) {{
  document.querySelectorAll('.log-filter').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('#logPanel .log-entry').forEach(entry => {{
    if (level === 'all') {{ entry.style.display = ''; }}
    else {{ entry.style.display = entry.classList.contains('log-' + level) || entry.classList.contains('trace-call') || entry.classList.contains('trace-result') || entry.classList.contains('trace-other') ? '' : 'none'; }}
  }});
}}
</script>
</body>
</html>'''

    out_path = run_dir / "analysis-report.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_out)
    logger.info(f"HTML report written: {out_path} ({os.path.getsize(out_path):,} bytes)")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.reports.html_report <run_dir>", file=sys.stderr)
        sys.exit(1)
    run_dir = Path(sys.argv[1])
    if not run_dir.exists():
        print(f"Error: Directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)
    path = generate_html_report(run_dir)
    print(f"HTML report: file://{path.resolve()}")
