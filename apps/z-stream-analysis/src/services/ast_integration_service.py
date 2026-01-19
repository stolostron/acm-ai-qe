#!/usr/bin/env python3
"""
AST Integration Service

Optional Node.js-based AST parsing for better selector resolution.
Falls back to regex-based resolution when Node.js is not available.

This service handles:
- Template literal resolution (e.g., `${prefix}-button`)
- Deep import tracing across module boundaries
- Custom command expansion for Cypress
- Testing Library query detection
"""

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Set


@dataclass
class ResolvedSelector:
    """A resolved selector with its origin."""
    selector: str
    original_expression: str  # The original code expression
    file_path: str  # Where it was found
    line_number: Optional[int] = None
    is_dynamic: bool = False  # True if it contains variables
    resolved_from: str = "regex"  # "ast" or "regex"


@dataclass
class ImportTrace:
    """Traced import with resolved path and exports."""
    import_statement: str
    source_file: str
    resolved_path: str
    exported_names: List[str] = field(default_factory=list)
    is_resolved: bool = False


@dataclass
class ASTAnalysisResult:
    """Complete AST analysis result for a file."""
    file_path: str
    selectors: List[ResolvedSelector] = field(default_factory=list)
    imports: List[ImportTrace] = field(default_factory=list)
    custom_commands: List[str] = field(default_factory=list)
    testing_library_queries: List[str] = field(default_factory=list)
    analysis_method: str = "regex"  # "ast" or "regex"
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "selectors": [
                {
                    "selector": s.selector,
                    "original_expression": s.original_expression,
                    "file_path": s.file_path,
                    "line_number": s.line_number,
                    "is_dynamic": s.is_dynamic,
                    "resolved_from": s.resolved_from,
                }
                for s in self.selectors
            ],
            "imports": [
                {
                    "import_statement": i.import_statement,
                    "resolved_path": i.resolved_path,
                    "exported_names": i.exported_names,
                    "is_resolved": i.is_resolved,
                }
                for i in self.imports
            ],
            "custom_commands": self.custom_commands,
            "testing_library_queries": self.testing_library_queries,
            "analysis_method": self.analysis_method,
            "errors": self.errors,
        }


class ASTIntegrationService:
    """
    Optional AST-based analysis for JavaScript/TypeScript files.

    Uses Node.js and TypeScript parser when available for accurate
    selector resolution. Falls back to regex patterns otherwise.
    """

    def __init__(self, ast_helper_path: Optional[str] = None):
        """
        Initialize AST Integration Service.

        Args:
            ast_helper_path: Path to Node.js AST helper. If None, uses regex fallback.
        """
        self.logger = logging.getLogger(__name__)
        self.ast_helper_path = ast_helper_path
        self.node_available = self._check_node_available()
        self.ast_available = self._check_ast_helper_available()

        if self.ast_available:
            self.logger.info("AST helper available - using AST-based analysis")
        else:
            self.logger.info("AST helper not available - using regex fallback")

    def _check_node_available(self) -> bool:
        """Check if Node.js is available."""
        try:
            result = subprocess.run(
                ['node', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self.logger.debug(f"Node.js available: {version}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return False

    def _check_ast_helper_available(self) -> bool:
        """Check if AST helper script is available and runnable."""
        if not self.node_available:
            return False

        if not self.ast_helper_path:
            return False

        helper_path = Path(self.ast_helper_path)
        if not helper_path.exists():
            return False

        # Try running the helper
        try:
            result = subprocess.run(
                ['node', str(helper_path), '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return False

    def analyze_file(
        self, repo_path: Path, file_path: str
    ) -> ASTAnalysisResult:
        """
        Analyze a JavaScript/TypeScript file for selectors.

        Args:
            repo_path: Path to the cloned repository
            file_path: Relative path to the file to analyze

        Returns:
            ASTAnalysisResult with selectors and imports
        """
        full_path = repo_path / file_path
        result = ASTAnalysisResult(file_path=file_path)

        if not full_path.exists():
            result.errors.append(f"File not found: {file_path}")
            return result

        if self.ast_available:
            return self._analyze_with_ast(repo_path, file_path)
        else:
            return self._analyze_with_regex(repo_path, file_path)

    def _analyze_with_ast(
        self, repo_path: Path, file_path: str
    ) -> ASTAnalysisResult:
        """Analyze file using Node.js AST parser."""
        result = ASTAnalysisResult(file_path=file_path, analysis_method="ast")
        full_path = repo_path / file_path

        try:
            # Run AST helper
            cmd = [
                'node', self.ast_helper_path,
                '--file', str(full_path),
                '--repo', str(repo_path),
                '--json'
            ]

            proc_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if proc_result.returncode == 0:
                data = json.loads(proc_result.stdout)

                # Parse selectors
                for s in data.get('selectors', []):
                    result.selectors.append(ResolvedSelector(
                        selector=s['selector'],
                        original_expression=s.get('expression', s['selector']),
                        file_path=file_path,
                        line_number=s.get('line'),
                        is_dynamic=s.get('is_dynamic', False),
                        resolved_from="ast"
                    ))

                # Parse imports
                for i in data.get('imports', []):
                    result.imports.append(ImportTrace(
                        import_statement=i.get('statement', ''),
                        source_file=file_path,
                        resolved_path=i.get('resolved_path', ''),
                        exported_names=i.get('exports', []),
                        is_resolved=i.get('is_resolved', False)
                    ))

                result.custom_commands = data.get('custom_commands', [])
                result.testing_library_queries = data.get('testing_library_queries', [])
            else:
                result.errors.append(f"AST helper failed: {proc_result.stderr}")
                # Fall back to regex
                return self._analyze_with_regex(repo_path, file_path)

        except subprocess.TimeoutExpired:
            result.errors.append("AST analysis timed out")
            return self._analyze_with_regex(repo_path, file_path)
        except json.JSONDecodeError as e:
            result.errors.append(f"Failed to parse AST output: {e}")
            return self._analyze_with_regex(repo_path, file_path)
        except Exception as e:
            result.errors.append(f"AST analysis error: {e}")
            return self._analyze_with_regex(repo_path, file_path)

        return result

    def _analyze_with_regex(
        self, repo_path: Path, file_path: str
    ) -> ASTAnalysisResult:
        """Analyze file using regex patterns (fallback)."""
        import re

        result = ASTAnalysisResult(file_path=file_path, analysis_method="regex")
        full_path = repo_path / file_path

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')

            # Selector patterns
            selector_patterns = [
                # cy.get('selector')
                (r"cy\.get\(['\"]([^'\"]+)['\"]\)", False),
                # cy.find('selector')
                (r"cy\.find\(['\"]([^'\"]+)['\"]\)", False),
                # data-test attributes
                (r"\[data-test(?:id)?=['\"]([^'\"]+)['\"]\]", False),
                # data-cy attributes
                (r"\[data-cy=['\"]([^'\"]+)['\"]\]", False),
                # Template literals (mark as dynamic)
                (r"cy\.get\(`([^`]+)`\)", True),
                (r"cy\.find\(`([^`]+)`\)", True),
            ]

            for pattern, is_dynamic in selector_patterns:
                for match in re.finditer(pattern, content):
                    selector = match.group(1)

                    # Find line number
                    start = match.start()
                    line_num = content[:start].count('\n') + 1

                    result.selectors.append(ResolvedSelector(
                        selector=selector,
                        original_expression=match.group(0),
                        file_path=file_path,
                        line_number=line_num,
                        is_dynamic=is_dynamic or '${' in selector,
                        resolved_from="regex"
                    ))

            # Import patterns
            import_patterns = [
                r"import\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"]",
                r"import\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]",
                r"const\s+\{([^}]+)\}\s*=\s*require\(['\"]([^'\"]+)['\"]\)",
            ]

            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    names = match.group(1).split(',')
                    names = [n.strip() for n in names]
                    path = match.group(2)

                    result.imports.append(ImportTrace(
                        import_statement=match.group(0),
                        source_file=file_path,
                        resolved_path=path,
                        exported_names=names,
                        is_resolved=False
                    ))

            # Custom commands
            command_pattern = r"Cypress\.Commands\.add\(['\"](\w+)['\"]"
            for match in re.finditer(command_pattern, content):
                result.custom_commands.append(match.group(1))

            # Testing Library queries
            tl_patterns = [
                r"\.findByRole\(['\"]([^'\"]+)['\"]",
                r"\.getByRole\(['\"]([^'\"]+)['\"]",
                r"\.findByText\(['\"]([^'\"]+)['\"]",
                r"\.getByText\(['\"]([^'\"]+)['\"]",
                r"\.findByTestId\(['\"]([^'\"]+)['\"]",
                r"\.getByTestId\(['\"]([^'\"]+)['\"]",
            ]

            for pattern in tl_patterns:
                for match in re.finditer(pattern, content):
                    result.testing_library_queries.append(match.group(0))

        except Exception as e:
            result.errors.append(f"Regex analysis error: {e}")

        return result

    def resolve_selector_chain(
        self,
        repo_path: Path,
        file_path: str,
        selector_expression: str
    ) -> List[ResolvedSelector]:
        """
        Trace a selector expression through imports to find all possible values.

        Args:
            repo_path: Path to the cloned repository
            file_path: File containing the selector expression
            selector_expression: The expression using the selector

        Returns:
            List of possible resolved selectors
        """
        resolved = []
        visited_files: Set[str] = set()

        def trace_imports(current_file: str, expression: str):
            if current_file in visited_files:
                return
            visited_files.add(current_file)

            analysis = self.analyze_file(repo_path, current_file)

            # Check if expression is defined in this file
            for selector in analysis.selectors:
                if expression in selector.original_expression:
                    resolved.append(selector)

            # Check imports
            for imp in analysis.imports:
                # See if the expression uses any imported names
                for name in imp.exported_names:
                    if name in expression:
                        # Resolve the import path
                        resolved_path = self._resolve_import_path(
                            current_file, imp.resolved_path
                        )
                        if resolved_path:
                            trace_imports(resolved_path, name)

        trace_imports(file_path, selector_expression)
        return resolved

    def _resolve_import_path(self, from_file: str, import_path: str) -> Optional[str]:
        """Resolve a relative import path to a file path."""
        if not import_path.startswith('.'):
            return None  # External module

        from_dir = Path(from_file).parent
        resolved = from_dir / import_path

        # Try common extensions
        extensions = ['.js', '.ts', '.jsx', '.tsx', '/index.js', '/index.ts']
        for ext in extensions:
            candidate = str(resolved) + ext
            if Path(candidate).exists():
                return candidate

        return str(resolved)

    def get_all_selectors_in_file(
        self, repo_path: Path, file_path: str, resolve_imports: bool = True
    ) -> List[ResolvedSelector]:
        """
        Get all selectors used in a file, optionally resolving imports.

        Args:
            repo_path: Path to the cloned repository
            file_path: File to analyze
            resolve_imports: Whether to trace imports for dynamic selectors

        Returns:
            List of all selectors found
        """
        analysis = self.analyze_file(repo_path, file_path)
        all_selectors = list(analysis.selectors)

        if resolve_imports:
            # For dynamic selectors, try to resolve them
            for selector in analysis.selectors:
                if selector.is_dynamic:
                    resolved = self.resolve_selector_chain(
                        repo_path, file_path, selector.original_expression
                    )
                    all_selectors.extend(resolved)

        return all_selectors


def create_ast_service(ast_helper_path: Optional[str] = None) -> ASTIntegrationService:
    """
    Create an AST integration service.

    If ast_helper_path is not provided, looks for ast_helper in:
    1. Environment variable AST_HELPER_PATH
    2. ./ast_helper/dist/index.js
    3. Falls back to regex-only mode
    """
    if not ast_helper_path:
        ast_helper_path = os.environ.get('AST_HELPER_PATH')

    if not ast_helper_path:
        default_path = Path(__file__).parent.parent.parent / 'ast_helper' / 'dist' / 'index.js'
        if default_path.exists():
            ast_helper_path = str(default_path)

    return ASTIntegrationService(ast_helper_path=ast_helper_path)
