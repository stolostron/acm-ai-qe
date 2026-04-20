"""Deterministic Polarion HTML generator from test case markdown.

Follows the fixed templates from polarion-html-templates.md:
- Inline styles with no space after semicolons
- Bold via <span style="font-weight:bold;"> not <b>
- Escape && as &amp;&amp;
- Line breaks as <br>
- Links as <a href="URL" target="_top">
"""

import re
from pathlib import Path
from typing import Optional

BASE_STYLE = 'font-size:11pt;font-family:Arial,Helvetica,sans-serif;color:#000000;line-height:1.5'
BOLD_STYLE = f'{BASE_STYLE};font-weight:bold'
CODE_STYLE = 'background-color:#f4f4f4;padding:10px;border:1px solid #ddd;border-radius:4px;font-family:monospace;font-size:10pt;white-space:pre-wrap;overflow-x:auto'


def _escape_html(text: str) -> str:
    """Escape HTML special characters per Polarion rules."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def _extract_section(content: str, section_name: str, next_sections: list[str]) -> Optional[str]:
    """Extract a markdown section between headers."""
    pattern = f"## {section_name}"
    start = content.find(pattern)
    if start < 0:
        return None

    start = content.find("\n", start) + 1

    end = len(content)
    for next_sec in next_sections:
        next_pattern = f"## {next_sec}"
        pos = content.find(next_pattern, start)
        if 0 < pos < end:
            end = pos

    return content[start:end].strip()


def generate_setup_html(content: str) -> str:
    """Generate Polarion-compatible HTML for the Setup section."""
    setup_text = _extract_section(content, "Setup", ["Test Steps", "Step 1"])
    if not setup_text:
        return ""

    html_parts = [f'<span style="{BASE_STYLE}">']

    lines = setup_text.split("\n")
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                html_parts.append("</pre>")
                in_code_block = False
            else:
                html_parts.append(f'<pre style="{CODE_STYLE}">')
                in_code_block = True
            continue

        if in_code_block:
            html_parts.append(_escape_html(line))
            continue

        if stripped.startswith("**") and stripped.endswith("**"):
            label = stripped.strip("*").strip(":")
            html_parts.append(f'<span style="{BOLD_STYLE}">{_escape_html(label)}:</span><br>')
        elif stripped.startswith("- "):
            bullet_text = stripped[2:]
            html_parts.append(f"&bull; {_escape_html(bullet_text)}<br>")
        elif stripped:
            html_parts.append(f"{_escape_html(stripped)}<br>")

    if in_code_block:
        html_parts.append("</pre>")

    html_parts.append("</span>")
    return "\n".join(html_parts)


def generate_steps_html(content: str) -> str:
    """Generate Polarion-compatible HTML for the Test Steps table."""
    step_pattern = re.compile(r"^### Step (\d+):\s*(.+)$", re.MULTILINE)
    matches = list(step_pattern.finditer(content))

    if not matches:
        return ""

    TH_STYLE = 'white-space:nowrap;height:12px;text-align:left;vertical-align:top;font-weight:bold;background-color:#F0F0F0;border:1px solid #CCCCCC;padding:5px;width:50%'
    TD_STYLE = 'height:12px;text-align:left;vertical-align:top;line-height:18px;border:1px solid #CCCCCC;padding:5px'

    rows = [
        "<table style=\"border-collapse:collapse;width:100%;\">",
        "<tbody>",
        f'<tr><th contenteditable="false" id="testStepKey:step" style="{TH_STYLE};">Step</th>'
        f'<th contenteditable="false" id="testStepKey:expectedResult" style="{TH_STYLE};">Expected Result</th></tr>',
    ]

    td_style = f'style="{TD_STYLE}"'

    for i, match in enumerate(matches):
        step_num = match.group(1)
        step_title = match.group(2).strip()

        # Extract step content until next step or section
        start = match.end()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            # Find the next ## section
            next_section = content.find("\n## ", start)
            end = next_section if next_section > 0 else len(content)

        step_content = content[start:end].strip()

        # Split into actions and expected result
        actions_text = ""
        expected_text = ""

        er_marker = "**Expected Result:**"
        er_pos = step_content.find(er_marker)
        if er_pos < 0:
            er_marker = "**Expected Result**"
            er_pos = step_content.find(er_marker)

        if er_pos >= 0:
            actions_text = step_content[:er_pos].strip()
            expected_text = step_content[er_pos + len(er_marker):].strip()
        else:
            actions_text = step_content

        # Format actions
        action_lines = []
        action_lines.append(f'<span style="font-weight:bold;">Step {step_num}: {_escape_html(step_title)}</span><br><br>')
        for line in actions_text.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("**Actions"):
                action_lines.append(f"{_escape_html(stripped)}<br>")
        actions_html = "\n".join(action_lines)

        # Format expected results
        expected_lines = []
        for line in expected_text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("- "):
                expected_lines.append(f"&bull; {_escape_html(stripped[2:])}<br>")
            elif stripped:
                expected_lines.append(f"{_escape_html(stripped)}<br>")
        expected_html = "\n".join(expected_lines)

        rows.append(
            f'<tr><td {td_style}><span style="{BASE_STYLE};">{actions_html}</span></td>'
            f'<td {td_style}><span style="{BASE_STYLE};">{expected_html}</span></td></tr>'
        )

    rows.append("</tbody>")
    rows.append("</table>")

    return "\n".join(rows)


def generate_html(test_case_path: str, output_dir: str) -> tuple[Optional[str], Optional[str]]:
    """Generate both setup and steps HTML files. Returns (setup_path, steps_path)."""
    path = Path(test_case_path)
    if not path.exists():
        return None, None

    content = path.read_text(encoding="utf-8")
    out = Path(output_dir)

    setup_html = generate_setup_html(content)
    steps_html = generate_steps_html(content)

    setup_path = None
    steps_path = None

    if setup_html:
        p = out / "test-case-setup.html"
        p.write_text(setup_html, encoding="utf-8")
        setup_path = str(p)

    if steps_html:
        p = out / "test-case-steps.html"
        p.write_text(steps_html, encoding="utf-8")
        steps_path = str(p)

    return setup_path, steps_path
