import re
import json
from typing import List, Dict, Any, Optional

class UIAnalyzer:
    def __init__(self):
        # Regex for finding test IDs and similar attributes
        # Matches: data-testid, data-test, data-test-id, id, aria-label
        self.attr_pattern = re.compile(
            r'(data-testid|data-test-id|data-test|id|aria-label)\s*=\s*["\']([^"\']+)["\']'
        )

        # Regex for finding component definitions
        # Matches: export const ComponentName = ... or function ComponentName(...)
        self.component_pattern = re.compile(
            r'export\s+(?:const|function)\s+([A-Z][a-zA-Z0-9]*)'
        )

        # Regex for TypeScript type/interface definitions
        self.type_pattern = re.compile(
            r'(?:export\s+)?(?:type|interface)\s+([A-Z][a-zA-Z0-9]*)\s*(?:<[^>]+>)?\s*=?\s*\{',
            re.MULTILINE
        )

        # Regex for wizard step patterns (PatternFly Wizard)
        self.wizard_step_pattern = re.compile(
            r'<WizardStep\s+[^>]*name\s*=\s*[{"\']([^"\'{}]+|\{[^}]+\})["\'}][^>]*>',
            re.MULTILINE | re.DOTALL
        )

        # Regex for isHidden conditions in wizard steps
        self.is_hidden_pattern = re.compile(
            r'isHidden\s*=\s*\{([^}]+)\}',
            re.MULTILINE
        )

    def extract_test_ids(self, content: str) -> List[Dict[str, str]]:
        """
        Extracts automation-relevant attributes from the code content.
        Returns a list of dicts with 'attribute', 'value', and 'context'.
        """
        results = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            for match in self.attr_pattern.finditer(line):
                attr_name = match.group(1)
                attr_value = match.group(2)

                # Get some context (previous and next line)
                start_line = max(0, i - 1)
                end_line = min(len(lines), i + 2)
                context = '\n'.join(lines[start_line:end_line]).strip()

                results.append({
                    "attribute": attr_name,
                    "value": attr_value,
                    "line": i + 1,
                    "context": context
                })
        return results

    def find_components(self, content: str) -> List[str]:
        """Finds component names defined in the file."""
        return self.component_pattern.findall(content)

    def analyze_route_file(self, content: str) -> List[Dict[str, str]]:
        """
        Analyzes a route definition file to find path mappings.
        This is a heuristic approach assuming standard React Router usage.
        """
        # Look for <Route path="..." component={...} /> or element={...}
        # This is complex to regex perfectly, but we can try simple patterns
        routes = []
        # Pattern for Route path
        route_pattern = re.compile(r'<Route\s+[^>]*path=["\']([^"\']+)["\']')

        for match in route_pattern.finditer(content):
            routes.append({"path": match.group(1)})

        return routes

    def extract_types(self, content: str) -> List[Dict[str, Any]]:
        """
        Extracts TypeScript type and interface definitions from content.
        Returns structured type information.
        """
        results = []
        lines = content.split('\n')

        # Find type/interface declarations
        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for type or interface declaration
            type_match = re.match(
                r'(?:export\s+)?(?:type|interface)\s+([A-Z][a-zA-Z0-9]*(?:<[^>]+>)?)\s*=?\s*\{?',
                line.strip()
            )

            if type_match:
                type_name = type_match.group(1)
                start_line = i + 1

                # Collect the full type definition
                brace_count = line.count('{') - line.count('}')
                type_lines = [line]

                # If we have an opening brace, find the closing one
                if brace_count > 0:
                    i += 1
                    while i < len(lines) and brace_count > 0:
                        type_lines.append(lines[i])
                        brace_count += lines[i].count('{') - lines[i].count('}')
                        i += 1
                    i -= 1  # Back up one since we'll increment at the end

                type_def = '\n'.join(type_lines)

                # Extract fields
                fields = self._extract_type_fields(type_def)

                results.append({
                    "name": type_name,
                    "line": start_line,
                    "definition": type_def.strip(),
                    "fields": fields
                })

            i += 1

        return results

    def _extract_type_fields(self, type_def: str) -> List[Dict[str, str]]:
        """Extracts field names and types from a type definition."""
        fields = []

        # Pattern to match field: type pairs
        field_pattern = re.compile(
            r'^\s*(\w+)\??:\s*(.+?)(?:;|$)',
            re.MULTILINE
        )

        for match in field_pattern.finditer(type_def):
            field_name = match.group(1)
            field_type = match.group(2).strip().rstrip(';')
            fields.append({
                "name": field_name,
                "type": field_type,
                "optional": '?' in match.group(0).split(':')[0]
            })

        return fields

    def extract_wizard_steps(self, content: str) -> List[Dict[str, Any]]:
        """
        Extracts wizard step information from a PatternFly wizard component.
        Returns step names, visibility conditions, and order.
        """
        results = []
        lines = content.split('\n')
        seen_steps = set()  # Track unique steps by id to avoid duplicates

        step_count = 0
        i = 0
        while i < len(lines):
            line = lines[i]

            # Look for WizardStep component
            if '<WizardStep' in line:
                step_info = {}

                # Get context - several lines around the step
                start = max(0, i)
                end = min(len(lines), i + 20)
                context = '\n'.join(lines[start:end])

                # Extract step name - handle various patterns
                # Pattern 1: name={t('Step Name')}
                name_match = re.search(r"name\s*=\s*\{\s*t\s*\(\s*['\"]([^'\"]+)['\"]", context)
                if name_match:
                    step_info["name"] = name_match.group(1)
                else:
                    # Pattern 2: name="Step Name"
                    name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', context)
                    if name_match:
                        step_info["name"] = name_match.group(1)

                # Extract id
                id_match = re.search(r'\bid\s*=\s*["\']([^"\']+)["\']', context)
                if id_match:
                    step_info["id"] = id_match.group(1)

                # Extract isHidden condition - handle multi-line
                hidden_match = re.search(r'isHidden\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}', context)
                if hidden_match:
                    hidden_cond = hidden_match.group(1).strip()
                    # Clean up whitespace
                    hidden_cond = ' '.join(hidden_cond.split())
                    step_info["isHidden"] = hidden_cond
                else:
                    step_info["isHidden"] = None

                # Only add if we found a name and it's unique
                if "name" in step_info:
                    step_id = step_info.get("id", step_info["name"])
                    if step_id not in seen_steps:
                        seen_steps.add(step_id)
                        step_count += 1
                        step_info["order"] = step_count
                        results.append(step_info)

            i += 1

        return results

    def search_translations(self, translations: Dict[str, str], query: str, exact: bool = False) -> List[Dict[str, str]]:
        """
        Searches translation keys/values for matching strings.

        Args:
            translations: Dict of translation key -> value
            query: Search term
            exact: If True, only return exact matches

        Returns:
            List of matching translations with key and value
        """
        results = []
        query_lower = query.lower()

        for key, value in translations.items():
            if exact:
                if query == key or query == value:
                    results.append({"key": key, "value": value})
            else:
                if query_lower in key.lower() or query_lower in str(value).lower():
                    results.append({"key": key, "value": value})

        return results

    def extract_navigation_paths(self, content: str) -> List[Dict[str, str]]:
        """
        Extracts NavigationPath enum values from ACM's NavigationPath.ts file.
        """
        results = []

        # Pattern to match NavigationPath enum entries
        # e.g., clusters = '/multicloud/infrastructure/clusters'
        path_pattern = re.compile(
            r"(\w+)\s*=\s*['\"]([^'\"]+)['\"]",
            re.MULTILINE
        )

        for match in path_pattern.finditer(content):
            name = match.group(1)
            path = match.group(2)
            results.append({
                "name": name,
                "path": path
            })

        return results
