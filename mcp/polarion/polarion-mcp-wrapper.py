#!/usr/bin/env python3
"""
Polarion MCP Wrapper - Patches SSL + adds enhanced tools for test case workflows.

Enhancements over base polarion-mcp:
- SSL verification disabled for Red Hat internal Polarion
- get_test_steps: Fetch test step content (step text + expected results)
- get_test_case_summary: Get setup, description, and step titles in one call
- Increased timeout for large requests (30s vs 8s)

Usage: python polarion-mcp-wrapper.py
"""

import os
import sys
import json
import re
import warnings

# Suppress SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Patch requests to disable SSL verification globally
import requests

_original_request = requests.Session.request

def _patched_request(self, method, url, **kwargs):
    if 'polarion' in url.lower():
        kwargs['verify'] = False
        kwargs.setdefault('timeout', 30)  # Increase timeout for Polarion
    return _original_request(self, method, url, **kwargs)

requests.Session.request = _patched_request

_original_get = requests.get
_original_post = requests.post

def _patched_get(url, **kwargs):
    if 'polarion' in url.lower():
        kwargs['verify'] = False
        kwargs.setdefault('timeout', 30)
    return _original_get(url, **kwargs)

def _patched_post(url, **kwargs):
    if 'polarion' in url.lower():
        kwargs['verify'] = False
        kwargs.setdefault('timeout', 30)
    return _original_post(url, **kwargs)

requests.get = _patched_get
requests.post = _patched_post


def _register_enhanced_tools():
    """Register additional tools on the existing MCP server instance."""
    from polarion_mcp.server import mcp, polarion_client
    
    POLARION_BASE_URL = os.getenv("POLARION_BASE_URL", "https://polarion.engineering.redhat.com/polarion")

    @mcp.tool()
    def get_polarion_test_steps(project_id: str, work_item_id: str) -> str:
        """
        <purpose>Fetch test step content (step text + expected results) for a test case</purpose>
        
        <when_to_use>
        - When you need to see the actual test step content in a Polarion test case
        - To compare Polarion test steps with local markdown test cases
        - To verify what's already in Polarion before updating
        - When generating HTML to add/replace test steps
        </when_to_use>
        
        <parameters>
        - project_id: Required. Project ID (e.g., "RHACM4K")
        - work_item_id: Required. Work item ID (e.g., "RHACM4K-61733")
        </parameters>
        
        <output>List of test steps with their step text and expected result HTML content</output>
        """
        try:
            polarion_client._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/workitems/{work_item_id}/teststeps"
            params = {'fields[teststeps]': '@all'}
            response = polarion_client.session.get(
                api_url, params=params, headers=polarion_client._headers(), timeout=30
            )
            
            if response.status_code != 200:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to fetch test steps: HTTP {response.status_code}"
                })
            
            data = response.json()
            steps = []
            
            for step_data in data.get('data', []):
                attrs = step_data.get('attributes', {})
                idx = attrs.get('index', '?')
                values = attrs.get('values', [])
                
                step_html = values[0].get('value', '') if len(values) > 0 else ''
                expected_html = values[1].get('value', '') if len(values) > 1 else ''
                
                # Extract plain text title from step HTML
                title_match = re.search(r'font-weight:\s*bold[^>]*>([^<]+)', step_html)
                title = title_match.group(1).strip() if title_match else f'Step {idx}'
                
                steps.append({
                    "index": idx,
                    "title": title,
                    "step_html": step_html,
                    "expected_result_html": expected_html
                })
            
            return json.dumps({
                "status": "success",
                "work_item_id": work_item_id,
                "step_count": len(steps),
                "steps": steps
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to fetch test steps: {str(e)}"
            })

    @mcp.tool()
    def get_polarion_test_case_summary(project_id: str, work_item_id: str) -> str:
        """
        <purpose>Get a concise summary of a test case: title, description, setup, and step titles</purpose>
        
        <when_to_use>
        - Quick overview of what's in a Polarion test case
        - Compare Polarion content with local markdown at a glance
        - Check if setup and test steps are populated
        - Before deciding what needs to be updated
        </when_to_use>
        
        <parameters>
        - project_id: Required. Project ID (e.g., "RHACM4K")
        - work_item_id: Required. Work item ID (e.g., "RHACM4K-61733")
        </parameters>
        
        <output>Concise summary with title, setup status, step count, and step titles</output>
        """
        try:
            polarion_client._ensure_token()
            
            # Fetch work item for title + setup
            wi_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/workitems/{work_item_id}"
            wi_resp = polarion_client.session.get(
                wi_url, 
                params={'fields[workitems]': 'id,title,status,setup,description'},
                headers=polarion_client._headers(), timeout=30
            )
            
            if wi_resp.status_code != 200:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to fetch work item: HTTP {wi_resp.status_code}"
                })
            
            wi_data = wi_resp.json().get('data', {}).get('attributes', {})
            title = wi_data.get('title', '?')
            status = wi_data.get('status', '?')
            
            setup = wi_data.get('setup', {})
            setup_html = setup.get('value', '') if isinstance(setup, dict) else ''
            has_setup = len(setup_html) > 50
            
            desc = wi_data.get('description', {})
            desc_html = desc.get('value', '') if isinstance(desc, dict) else ''
            
            # Fetch test steps for titles
            ts_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/workitems/{work_item_id}/teststeps"
            ts_resp = polarion_client.session.get(
                ts_url,
                params={'fields[teststeps]': '@all'},
                headers=polarion_client._headers(), timeout=30
            )
            
            step_titles = []
            if ts_resp.status_code == 200:
                ts_data = ts_resp.json()
                for step_data in ts_data.get('data', []):
                    attrs = step_data.get('attributes', {})
                    idx = attrs.get('index', '?')
                    values = attrs.get('values', [])
                    step_html = values[0].get('value', '') if values else ''
                    title_match = re.search(r'font-weight:\s*bold[^>]*>([^<]+)', step_html)
                    step_title = title_match.group(1).strip() if title_match else f'Step {idx}'
                    step_titles.append(f"Step {idx}: {step_title}")
            
            return json.dumps({
                "status": "success",
                "work_item_id": work_item_id,
                "title": title,
                "status": status,
                "has_setup": has_setup,
                "setup_length": len(setup_html),
                "step_count": len(step_titles),
                "step_titles": step_titles
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to fetch summary: {str(e)}"
            })

    @mcp.tool()
    def get_polarion_setup_html(project_id: str, work_item_id: str) -> str:
        """
        <purpose>Get just the Setup section HTML from a Polarion test case</purpose>
        
        <when_to_use>
        - When you need to see or compare the current setup content
        - Before updating the setup section
        - To verify setup was pushed correctly
        </when_to_use>
        
        <parameters>
        - project_id: Required. Project ID (e.g., "RHACM4K")
        - work_item_id: Required. Work item ID (e.g., "RHACM4K-61733")
        </parameters>
        
        <output>The raw HTML content of the Setup section</output>
        """
        try:
            polarion_client._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/workitems/{work_item_id}"
            params = {'fields[workitems]': 'setup'}
            response = polarion_client.session.get(
                api_url, params=params, headers=polarion_client._headers(), timeout=30
            )
            
            if response.status_code != 200:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to fetch setup: HTTP {response.status_code}"
                })
            
            data = response.json()
            setup = data.get('data', {}).get('attributes', {}).get('setup', {})
            setup_html = setup.get('value', '') if isinstance(setup, dict) else ''
            
            return json.dumps({
                "status": "success",
                "work_item_id": work_item_id,
                "has_content": len(setup_html) > 50,
                "html_length": len(setup_html),
                "html": setup_html
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Failed to fetch setup: {str(e)}"
            })

    print("Enhanced tools registered: get_polarion_test_steps, get_polarion_test_case_summary, get_polarion_setup_html", file=sys.stderr)


if __name__ == "__main__":
    print("Polarion MCP Wrapper: SSL disabled + enhanced tools loading...", file=sys.stderr)
    
    try:
        # Register enhanced tools before running
        _register_enhanced_tools()
        
        from polarion_mcp.server import run
        run()
    except ImportError as e:
        print(f"Error: Could not import polarion_mcp: {e}", file=sys.stderr)
        print("Try: pip install polarion-mcp", file=sys.stderr)
        sys.exit(1)
