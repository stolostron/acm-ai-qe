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
from datetime import datetime, timezone

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

    # ===================================================================
    # READ TOOLS - Test Runs and Plans
    # ===================================================================

    @mcp.tool()
    def list_polarion_test_runs(project_id: str, query: str = "", limit: int = 20, page_number: int = 1) -> str:
        """
        <purpose>List and filter test runs in a Polarion project</purpose>

        <when_to_use>
        - Find test runs for a specific release plan (e.g., ACM_2_16)
        - List test runs by status (finished, inprogress, open)
        - Search test runs by title or other criteria
        - Get an overview of test execution for a project
        </when_to_use>

        <parameters>
        - project_id: Required. Project ID (e.g., "RHACM4K")
        - query: Optional. Lucene query to filter test runs.
          Examples: "status:finished", "plannedin.KEY:ACM_2_16", "title:ServerFoundation"
        - limit: Optional. Max results per page (default 20, max 100)
        - page_number: Optional. Page number for pagination (default 1)
        </parameters>

        <output>List of test runs with ID, title, status, and dates</output>
        """
        try:
            polarion_client._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/testruns"

            params = {
                'page[size]': min(limit, 100),
                'page[number]': page_number,
                'fields[testruns]': 'id,title,status,created,updated,isTemplate'
            }
            if query:
                params['query'] = query

            response = polarion_client.session.get(
                api_url, params=params, headers=polarion_client._headers(), timeout=30
            )

            if response.status_code != 200:
                return json.dumps({"status": "error", "message": f"HTTP {response.status_code}: {response.text[:300]}"})

            data = response.json()
            runs = []
            for item in data.get('data', []):
                attrs = item.get('attributes', {})
                runs.append({
                    "id": item.get('id', '').split('/')[-1],
                    "title": attrs.get('title', ''),
                    "status": attrs.get('status', ''),
                    "created": attrs.get('created', ''),
                    "updated": attrs.get('updated', ''),
                    "is_template": attrs.get('isTemplate', False)
                })

            total = data.get('meta', {}).get('total', len(runs))

            return json.dumps({
                "status": "success",
                "project_id": project_id,
                "total": total,
                "page": page_number,
                "page_size": min(limit, 100),
                "count": len(runs),
                "test_runs": runs
            }, indent=2)

        except Exception as e:
            return json.dumps({"status": "error", "message": f"Failed to list test runs: {str(e)}"})

    @mcp.tool()
    def get_polarion_test_run_info(project_id: str, test_run_id: str, include_records: bool = False) -> str:
        """
        <purpose>Get detailed test run info including pass/fail/blocked statistics</purpose>

        <when_to_use>
        - Get pass/fail/blocked statistics for a test run
        - See test run metadata (title, status, dates, plan)
        - Get individual test case results (with include_records=True)
        </when_to_use>

        <parameters>
        - project_id: Required. Project ID (e.g., "RHACM4K")
        - test_run_id: Required. Test run ID (e.g., "ACM-TestRun-2024-01")
        - include_records: Optional. Include individual test case results (default False)
        </parameters>

        <output>Test run details with statistics and optional test records</output>
        """
        try:
            polarion_client._ensure_token()
            base = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/testruns/{test_run_id}"

            # Get test run info
            resp = polarion_client.session.get(
                base,
                params={'fields[testruns]': 'id,title,status,created,updated,isTemplate,finishedOn,plannedin'},
                headers=polarion_client._headers(), timeout=30
            )

            if resp.status_code != 200:
                return json.dumps({"status": "error", "message": f"HTTP {resp.status_code}: {resp.text[:300]}"})

            run_data = resp.json().get('data', {})
            attrs = run_data.get('attributes', {})

            result = {
                "id": test_run_id,
                "title": attrs.get('title', ''),
                "status": attrs.get('status', ''),
                "created": attrs.get('created', ''),
                "updated": attrs.get('updated', ''),
                "is_template": attrs.get('isTemplate', False),
                "finished_on": attrs.get('finishedOn', ''),
            }

            # Get test records for statistics (paginate, max 100 per page)
            records_url = f"{base}/testrecords"
            records_data = []
            page = 1
            while True:
                rec_resp = polarion_client.session.get(
                    records_url,
                    params={'page[size]': 100, 'page[number]': page, 'fields[testrecords]': 'result,comment,executed,testCaseURI'},
                    headers=polarion_client._headers(), timeout=30
                )
                if rec_resp.status_code != 200:
                    break
                page_data = rec_resp.json().get('data', [])
                if not page_data:
                    break
                records_data.extend(page_data)
                if len(page_data) < 100:
                    break
                page += 1

            if records_data:
                stats = {"passed": 0, "failed": 0, "blocked": 0, "other": 0, "total": 0}
                records = []

                for rec in records_data:
                    rec_attrs = rec.get('attributes', {})
                    rec_result = rec_attrs.get('result', 'unknown')
                    result_id = rec_result.get('id', 'unknown') if isinstance(rec_result, dict) else str(rec_result)

                    stats['total'] += 1
                    if 'pass' in result_id.lower():
                        stats['passed'] += 1
                    elif 'fail' in result_id.lower():
                        stats['failed'] += 1
                    elif 'block' in result_id.lower():
                        stats['blocked'] += 1
                    else:
                        stats['other'] += 1

                    if include_records:
                        records.append({
                            "test_case": rec_attrs.get('testCaseURI', ''),
                            "result": result_id,
                            "executed": rec_attrs.get('executed', ''),
                            "comment": rec_attrs.get('comment', '')
                        })

                stats['pass_rate'] = round(stats['passed'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0.0
                result['statistics'] = stats

                if include_records:
                    result['records'] = records

            return json.dumps({"status": "success", **result}, indent=2)

        except Exception as e:
            return json.dumps({"status": "error", "message": f"Failed to get test run: {str(e)}"})

    @mcp.tool()
    def list_polarion_plans(project_id: str, query: str = "", status: str = "", limit: int = 20, page_number: int = 1) -> str:
        """
        <purpose>List and search test plans in a Polarion project</purpose>

        <when_to_use>
        - Find release plans (e.g., ACM_2_16, MCE_2_8)
        - List plans by status (open, closed)
        - Search plans by name or ID
        - Get plan IDs for use with test run queries
        </when_to_use>

        <parameters>
        - project_id: Required. Project ID (e.g., "RHACM4K")
        - query: Optional. Lucene query to filter plans. Example: "name:ACM_2_16"
        - status: Optional. Filter by status: "open" or "closed"
        - limit: Optional. Max results per page (default 20, max 100)
        - page_number: Optional. Page number for pagination (default 1)
        </parameters>

        <output>List of plans with ID, name, status, and dates</output>
        """
        try:
            polarion_client._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/plans"

            query_parts = []
            if query:
                query_parts.append(query)
            if status:
                query_parts.append(f'status:{status}')

            params = {
                'page[size]': min(limit, 100),
                'page[number]': page_number,
                'fields[plans]': 'id,name,status,created,updated,dueDate,startDate'
            }
            if query_parts:
                params['query'] = ' AND '.join(query_parts)

            response = polarion_client.session.get(
                api_url, params=params, headers=polarion_client._headers(), timeout=30
            )

            if response.status_code != 200:
                return json.dumps({"status": "error", "message": f"HTTP {response.status_code}: {response.text[:300]}"})

            data = response.json()
            plans = []
            for item in data.get('data', []):
                attrs = item.get('attributes', {})
                plan_id = item.get('id', '').split('/')[-1]
                plans.append({
                    "id": plan_id,
                    "name": attrs.get('name', plan_id),
                    "status": attrs.get('status', ''),
                    "created": attrs.get('created', ''),
                    "due_date": attrs.get('dueDate', ''),
                    "start_date": attrs.get('startDate', ''),
                })

            total = data.get('meta', {}).get('total', len(plans))

            return json.dumps({
                "status": "success",
                "project_id": project_id,
                "total": total,
                "page": page_number,
                "page_size": min(limit, 100),
                "count": len(plans),
                "plans": plans
            }, indent=2)

        except Exception as e:
            return json.dumps({"status": "error", "message": f"Failed to list plans: {str(e)}"})

    # ===================================================================
    # WRITE TOOLS - Work Items
    # ===================================================================

    @mcp.tool()
    def update_polarion_work_item(project_id: str, work_item_id: str, title: str = "", description_html: str = "", status: str = "", setup_html: str = "", custom_fields_json: str = "") -> str:
        """
        <purpose>Update fields on a Polarion work item (test case, requirement, etc.)</purpose>

        <when_to_use>
        - Change work item status (e.g., proposed -> approved)
        - Update title or description
        - Push setup section HTML content
        - Set custom field values
        - Any field modification on a work item
        </when_to_use>

        <parameters>
        - project_id: Required. Project ID (e.g., "RHACM4K")
        - work_item_id: Required. Work item ID (e.g., "RHACM4K-61726")
        - title: Optional. New title (leave empty to skip)
        - description_html: Optional. New description as HTML (leave empty to skip)
        - status: Optional. New status (e.g., "proposed", "approved", "inactive")
        - setup_html: Optional. New setup section as HTML (leave empty to skip)
        - custom_fields_json: Optional. JSON string of custom fields, e.g., '{"caseimportance": "high"}'
        </parameters>

        <output>Success/failure with updated field names</output>

        <warning>WRITE operation - modifies Polarion data. Verify changes before calling.</warning>
        """
        try:
            polarion_client._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/workitems/{work_item_id}"

            attributes = {}
            updated_fields = []

            if title:
                attributes['title'] = title
                updated_fields.append('title')
            if description_html:
                attributes['description'] = {'type': 'text/html', 'value': description_html}
                updated_fields.append('description')
            if status:
                attributes['status'] = status
                updated_fields.append('status')
            if setup_html:
                attributes['setup'] = {'type': 'text/html', 'value': setup_html}
                updated_fields.append('setup')
            if custom_fields_json:
                try:
                    custom = json.loads(custom_fields_json)
                    attributes.update(custom)
                    updated_fields.extend(custom.keys())
                except json.JSONDecodeError as e:
                    return json.dumps({"status": "error", "message": f"Invalid custom_fields_json: {e}"})

            if not attributes:
                return json.dumps({"status": "error", "message": "No fields to update. Provide at least one of: title, description_html, status, setup_html, custom_fields_json"})

            payload = {
                'data': {
                    'type': 'workitems',
                    'id': f'{project_id}/{work_item_id}',
                    'attributes': attributes
                }
            }

            response = polarion_client.session.patch(
                api_url, json=payload, headers=polarion_client._headers(), timeout=30
            )

            if response.status_code == 204:
                return json.dumps({
                    "status": "success",
                    "work_item_id": work_item_id,
                    "updated_fields": updated_fields,
                    "message": f"Successfully updated: {', '.join(updated_fields)}"
                }, indent=2)
            else:
                return json.dumps({
                    "status": "error",
                    "http_status": response.status_code,
                    "message": f"PATCH failed: {response.text[:500]}"
                })

        except Exception as e:
            return json.dumps({"status": "error", "message": f"Failed to update work item: {str(e)}"})

    @mcp.tool()
    def update_polarion_setup(project_id: str, work_item_id: str, setup_html: str) -> str:
        """
        <purpose>Update the Setup section of a Polarion test case with HTML content</purpose>

        <when_to_use>
        - Push locally-written setup content to Polarion
        - Replace the current setup section with new HTML
        - Pair with get_polarion_setup_html to read-then-update
        </when_to_use>

        <parameters>
        - project_id: Required. Project ID (e.g., "RHACM4K")
        - work_item_id: Required. Work item ID (e.g., "RHACM4K-61733")
        - setup_html: Required. HTML content for the setup section
        </parameters>

        <output>Success/failure confirmation</output>

        <warning>WRITE operation - replaces the entire Setup section.</warning>
        """
        try:
            polarion_client._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/workitems/{work_item_id}"

            payload = {
                'data': {
                    'type': 'workitems',
                    'id': f'{project_id}/{work_item_id}',
                    'attributes': {
                        'setup': {'type': 'text/html', 'value': setup_html}
                    }
                }
            }

            response = polarion_client.session.patch(
                api_url, json=payload, headers=polarion_client._headers(), timeout=30
            )

            if response.status_code == 204:
                return json.dumps({
                    "status": "success",
                    "work_item_id": work_item_id,
                    "message": "Setup section updated successfully",
                    "html_length": len(setup_html)
                }, indent=2)
            else:
                return json.dumps({
                    "status": "error",
                    "http_status": response.status_code,
                    "message": f"PATCH failed: {response.text[:500]}"
                })

        except Exception as e:
            return json.dumps({"status": "error", "message": f"Failed to update setup: {str(e)}"})

    @mcp.tool()
    def update_polarion_test_steps(project_id: str, work_item_id: str, steps_json: str) -> str:
        """
        <purpose>Create or update test steps on a Polarion test case</purpose>

        <when_to_use>
        - Push locally-written test steps to Polarion
        - Update existing test step content in-place
        - Create test steps on a test case that has none
        - Sync local markdown test steps with Polarion
        </when_to_use>

        <parameters>
        - project_id: Required. Project ID (e.g., "RHACM4K")
        - work_item_id: Required. Work item ID (e.g., "RHACM4K-61733")
        - steps_json: Required. JSON array of steps, each with "step_html" and "expected_result_html".
          Example: [{"step_html": "<p><b>Step Title</b></p><p>Details</p>", "expected_result_html": "<p>Expected</p>"}]
        </parameters>

        <output>Success/failure with count of steps written</output>

        <behavior>
        - If NO steps exist: Creates all steps via POST (bulk creation).
        - If steps ALREADY exist: PATCHes each existing step in-place (1-indexed).
          If new count > existing: updates existing steps, reports extras could not be added.
          If new count < existing: updates provided steps, extra existing steps remain unchanged.
          If counts match: all steps updated.
        </behavior>

        <warning>WRITE operation. When steps exist, updates content in-place via PATCH.</warning>
        """
        try:
            polarion_client._ensure_token()
            base_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/workitems/{work_item_id}/teststeps"
            hdrs = polarion_client._headers()

            # Parse steps
            try:
                steps = json.loads(steps_json)
                if not isinstance(steps, list):
                    return json.dumps({"status": "error", "message": "steps_json must be a JSON array"})
            except json.JSONDecodeError as e:
                return json.dumps({"status": "error", "message": f"Invalid steps_json: {e}"})

            # Get current steps
            get_resp = polarion_client.session.get(
                base_url, params={'fields[teststeps]': 'index'}, headers=hdrs, timeout=30
            )

            existing_count = 0
            if get_resp.status_code == 200:
                existing_steps = get_resp.json().get('data', [])
                existing_count = len(existing_steps)

            if existing_count == 0:
                # NO STEPS EXIST: Bulk POST creation
                post_data = []
                for step in steps:
                    post_data.append({
                        'type': 'teststeps',
                        'attributes': {
                            'keys': ['step', 'expectedResult'],
                            'values': [
                                {'type': 'text/html', 'value': step.get('step_html', '')},
                                {'type': 'text/html', 'value': step.get('expected_result_html', '')}
                            ]
                        }
                    })

                post_resp = polarion_client.session.post(
                    base_url, json={'data': post_data}, headers=hdrs, timeout=30
                )

                if post_resp.status_code in (200, 201, 204):
                    return json.dumps({
                        "status": "success",
                        "work_item_id": work_item_id,
                        "mode": "created",
                        "created": len(steps),
                        "message": f"Created {len(steps)} new test steps"
                    }, indent=2)
                else:
                    return json.dumps({
                        "status": "error",
                        "message": f"POST failed: HTTP {post_resp.status_code} - {post_resp.text[:500]}"
                    })

            else:
                # STEPS EXIST: PATCH each step in-place (1-indexed)
                updated = 0
                errors = []
                patchable = min(len(steps), existing_count)

                for idx in range(patchable):
                    step = steps[idx]
                    step_index = idx + 1  # Polarion test steps are 1-indexed

                    patch_payload = {
                        'data': {
                            'type': 'teststeps',
                            'id': f'{project_id}/{work_item_id}/{step_index}',
                            'attributes': {
                                'keys': ['step', 'expectedResult'],
                                'values': [
                                    {'type': 'text/html', 'value': step.get('step_html', '')},
                                    {'type': 'text/html', 'value': step.get('expected_result_html', '')}
                                ]
                            }
                        }
                    }

                    patch_resp = polarion_client.session.patch(
                        f"{base_url}/{step_index}", json=patch_payload, headers=hdrs, timeout=30
                    )

                    if patch_resp.status_code in (200, 204):
                        updated += 1
                    else:
                        errors.append(f"Step {step_index}: HTTP {patch_resp.status_code} - {patch_resp.text[:200]}")

                result = {
                    "status": "success" if not errors else "partial",
                    "work_item_id": work_item_id,
                    "mode": "patched",
                    "existing_steps": existing_count,
                    "new_steps_provided": len(steps),
                    "updated": updated,
                }

                if len(steps) > existing_count:
                    result["skipped"] = len(steps) - existing_count
                    result["note"] = f"{len(steps) - existing_count} extra steps could not be added (POST blocked when steps exist). Match step count to existing ({existing_count}) or start from empty."
                elif len(steps) < existing_count:
                    result["unchanged"] = existing_count - len(steps)
                    result["note"] = f"{existing_count - len(steps)} trailing steps left unchanged (DELETE not permitted)."

                if errors:
                    result["errors"] = errors

                result["message"] = f"Patched {updated}/{patchable} steps in-place"
                return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({"status": "error", "message": f"Failed to update test steps: {str(e)}"})

    # ===================================================================
    # WRITE TOOLS - Test Runs
    # ===================================================================

    @mcp.tool()
    def create_polarion_test_run(project_id: str, test_run_id: str, title: str, plan_id: str = "", custom_fields_json: str = "") -> str:
        """
        <purpose>Create a new test run in Polarion, optionally associated with a plan</purpose>

        <when_to_use>
        - Create a test run for reporting automation results
        - Set up a test run for a specific release plan
        - Create test runs for CI/CD pipeline integration
        </when_to_use>

        <parameters>
        - project_id: Required. Project ID (e.g., "RHACM4K")
        - test_run_id: Required. Unique ID for the test run (e.g., "Virt-RBAC-ACM216-Run1")
        - title: Required. Human-readable title
        - plan_id: Optional. Plan ID to associate with (e.g., "ACM_2_16"). Uses 'plannedin' field.
        - custom_fields_json: Optional. JSON string of custom fields, e.g., '{"type": "manual"}'
        </parameters>

        <output>Created test run details with plan association status</output>

        <warning>WRITE operation - creates a new test run in Polarion.</warning>
        """
        try:
            polarion_client._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/testruns"
            hdrs = polarion_client._headers()

            attributes = {
                'id': test_run_id,
                'title': title,
            }

            if custom_fields_json:
                try:
                    custom = json.loads(custom_fields_json)
                    attributes.update(custom)
                except json.JSONDecodeError as e:
                    return json.dumps({"status": "error", "message": f"Invalid custom_fields_json: {e}"})

            payload = {
                'data': [{
                    'type': 'testruns',
                    'attributes': attributes
                }]
            }

            # Step 1: Create the test run
            response = polarion_client.session.post(
                api_url, json=payload, headers=hdrs, timeout=30
            )

            if response.status_code not in (200, 201, 204):
                return json.dumps({
                    "status": "error",
                    "http_status": response.status_code,
                    "message": f"Failed to create test run: {response.text[:500]}"
                })

            result = {
                "status": "success",
                "test_run_id": test_run_id,
                "title": title,
                "message": "Test run created successfully"
            }

            # Step 2: Associate with plan if specified (requires separate PATCH)
            if plan_id:
                patch_url = f"{api_url}/{test_run_id}"
                patch_payload = {
                    'data': {
                        'type': 'testruns',
                        'id': f'{project_id}/{test_run_id}',
                        'attributes': {
                            'plannedin': plan_id
                        }
                    }
                }

                patch_resp = polarion_client.session.patch(
                    patch_url, json=patch_payload, headers=hdrs, timeout=30
                )

                if patch_resp.status_code == 204:
                    result['plan_id'] = plan_id
                    result['plan_associated'] = True
                else:
                    result['plan_associated'] = False
                    result['plan_error'] = f"Plan association failed: HTTP {patch_resp.status_code} - {patch_resp.text[:200]}"

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({"status": "error", "message": f"Failed to create test run: {str(e)}"})

    @mcp.tool()
    def upload_polarion_test_results(project_id: str, test_run_id: str, results_json: str) -> str:
        """
        <purpose>Upload test execution results to an existing Polarion test run</purpose>

        <when_to_use>
        - Report automation test results to a Polarion test run
        - Set pass/fail/blocked status for individual test cases in a run
        - Add execution comments to test records
        </when_to_use>

        <parameters>
        - project_id: Required. Project ID (e.g., "RHACM4K")
        - test_run_id: Required. Existing test run ID
        - results_json: Required. JSON array of results:
          [{"test_case_id": "RHACM4K-61726", "result": "passed", "comment": "optional"}]
          Valid results: "passed", "failed", "blocked"
        </parameters>

        <output>Upload summary with success/failure count</output>

        <warning>WRITE operation - adds/updates test records in a test run.</warning>
        """
        try:
            polarion_client._ensure_token()
            api_url = f"{POLARION_BASE_URL}/rest/v1/projects/{project_id}/testruns/{test_run_id}/testrecords"
            hdrs = polarion_client._headers()

            # Parse results
            try:
                results = json.loads(results_json)
                if not isinstance(results, list):
                    return json.dumps({"status": "error", "message": "results_json must be a JSON array"})
            except json.JSONDecodeError as e:
                return json.dumps({"status": "error", "message": f"Invalid results_json: {e}"})

            uploaded = 0
            errors = []

            for res in results:
                tc_id = res.get('test_case_id', '')
                result_val = res.get('result', 'passed')
                comment = res.get('comment', '')

                if not tc_id:
                    errors.append("Missing test_case_id in result entry")
                    continue

                # Ensure full ID format: PROJECT/WORK_ITEM_ID
                full_tc_id = tc_id if '/' in tc_id else f'{project_id}/{tc_id}'

                attrs = {
                    'result': result_val,
                    'executed': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
                }

                if comment:
                    attrs['comment'] = {'type': 'text/html', 'value': f'<p>{comment}</p>'}

                payload = {
                    'data': [{
                        'type': 'testrecords',
                        'attributes': attrs,
                        'relationships': {
                            'testCase': {
                                'data': {
                                    'type': 'workitems',
                                    'id': full_tc_id
                                }
                            }
                        }
                    }]
                }

                resp = polarion_client.session.post(
                    api_url, json=payload, headers=hdrs, timeout=30
                )

                if resp.status_code in (200, 201, 204):
                    uploaded += 1
                else:
                    errors.append(f"{tc_id}: HTTP {resp.status_code} - {resp.text[:200]}")

            return json.dumps({
                "status": "success" if not errors else "partial",
                "test_run_id": test_run_id,
                "uploaded": uploaded,
                "total": len(results),
                "errors": errors if errors else [],
                "message": f"Uploaded {uploaded}/{len(results)} test results"
            }, indent=2)

        except Exception as e:
            return json.dumps({"status": "error", "message": f"Failed to upload results: {str(e)}"})

    # Registration summary
    all_tools = [
        "get_polarion_test_steps", "get_polarion_test_case_summary", "get_polarion_setup_html",
        "list_polarion_test_runs", "get_polarion_test_run_info", "list_polarion_plans",
        "update_polarion_work_item", "update_polarion_setup", "update_polarion_test_steps",
        "create_polarion_test_run", "upload_polarion_test_results"
    ]
    print(f"Enhanced tools registered ({len(all_tools)}): {', '.join(all_tools)}", file=sys.stderr)


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
