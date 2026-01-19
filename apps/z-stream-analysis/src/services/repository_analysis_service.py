#!/usr/bin/env python3
"""
Repository Analysis Service
Real git clone and repository file analysis for test automation codebases

Usage:
    Analyzes cloned repositories for test patterns, dependencies, and code structure.
    Uses git for cloning and Python for file analysis.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class DependencyInfo:
    """Package dependency information"""
    name: str
    version: str
    is_dev: bool


@dataclass
class TestFileInfo:
    """Test file information"""
    path: str
    test_framework: str
    test_count: int
    selectors: List[str]


@dataclass
class SelectorHistory:
    """Git history for a selector"""
    selector: str
    file_path: str
    last_modified_date: Optional[str] = None
    last_commit_sha: Optional[str] = None
    last_commit_message: Optional[str] = None
    days_since_modified: Optional[int] = None


@dataclass
class RepositoryAnalysisResult:
    """Complete repository analysis result"""
    repository_url: str
    branch: str
    commit_sha: Optional[str]
    repository_cloned: bool
    clone_path: Optional[str]
    test_files: List[TestFileInfo]
    dependency_analysis: Dict[str, Any]
    code_patterns: Dict[str, Any]
    analysis_timestamp: float
    analysis_errors: List[str]
    # New fields for targeted extraction
    selector_lookup: Dict[str, List[str]] = None  # selector -> list of files
    selector_history: Dict[str, Dict[str, Any]] = None  # selector -> history info
    file_contents: Dict[str, str] = None  # file_path -> content around failure

    def __post_init__(self):
        if self.selector_lookup is None:
            self.selector_lookup = {}
        if self.selector_history is None:
            self.selector_history = {}
        if self.file_contents is None:
            self.file_contents = {}


class RepositoryAnalysisService:
    """
    Repository Analysis Service
    Real git clone and test file analysis
    """
    
    # Known test automation repositories
    KNOWN_REPOS = {
        'clc-e2e': 'https://github.com/stolostron/clc-ui-e2e.git',
        'clc-ui-e2e': 'https://github.com/stolostron/clc-ui-e2e.git',
        'console-e2e': 'https://github.com/stolostron/console-e2e.git',
        'acm-e2e': 'https://github.com/stolostron/acm-e2e.git',
    }
    
    # Test file patterns for different frameworks
    TEST_PATTERNS = {
        'cypress': [
            r'.*\.cy\.(js|ts)$',
            r'.*\.spec\.(js|ts)$',
            r'.*_spec\.(js|ts)$',
            r'cypress/.*\.(js|ts)$',
        ],
        'jest': [
            r'.*\.test\.(js|ts|jsx|tsx)$',
            r'.*\.spec\.(js|ts|jsx|tsx)$',
            r'__tests__/.*\.(js|ts|jsx|tsx)$',
        ],
        'playwright': [
            r'.*\.spec\.(js|ts)$',
            r'tests/.*\.(js|ts)$',
        ],
        'pytest': [
            r'test_.*\.py$',
            r'.*_test\.py$',
            r'tests/.*\.py$',
        ],
    }
    
    # Selector patterns to detect in test files
    SELECTOR_PATTERNS = [
        r'data-test(?:id)?=["\']([^"\']+)["\']',
        r'data-cy=["\']([^"\']+)["\']',
        r'cy\.get\(["\']([^"\']+)["\']\)',
        r'\.getByTestId\(["\']([^"\']+)["\']\)',
        r'\.getByRole\(["\']([^"\']+)["\']',
        r'\[data-test(?:id)?=["\']([^"\']+)["\']\]',
    ]
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize Repository Analysis Service.
        
        Args:
            base_path: Base directory for cloning repositories
                      Default: /tmp/z-stream-repos
        """
        self.logger = logging.getLogger(__name__)
        self.base_path = Path(base_path or '/tmp/z-stream-repos')
        
        # Create base directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Repository base path: {self.base_path}")
    
    def analyze_repository(self, 
                          repo_url: Optional[str] = None,
                          branch: Optional[str] = None,
                          job_name: Optional[str] = None) -> RepositoryAnalysisResult:
        """
        Clone and analyze a repository.
        
        Args:
            repo_url: Git repository URL (can be inferred from job_name)
            branch: Branch to checkout (default: main/master)
            job_name: Jenkins job name to infer repository
            
        Returns:
            RepositoryAnalysisResult: Complete analysis result
        """
        analysis_timestamp = time.time()
        analysis_errors = []
        
        # Resolve repository URL
        if not repo_url and job_name:
            repo_url = self._infer_repo_from_job(job_name)
        
        if not repo_url:
            return RepositoryAnalysisResult(
                repository_url='',
                branch=branch or '',
                commit_sha=None,
                repository_cloned=False,
                clone_path=None,
                test_files=[],
                dependency_analysis={},
                code_patterns={},
                analysis_timestamp=analysis_timestamp,
                analysis_errors=['No repository URL provided or could be inferred']
            )
        
        # Clone the repository
        clone_path, commit_sha, clone_error = self._clone_repository(repo_url, branch)
        
        if clone_error:
            analysis_errors.append(clone_error)
            return RepositoryAnalysisResult(
                repository_url=repo_url,
                branch=branch or 'main',
                commit_sha=None,
                repository_cloned=False,
                clone_path=None,
                test_files=[],
                dependency_analysis={},
                code_patterns={},
                analysis_timestamp=analysis_timestamp,
                analysis_errors=analysis_errors
            )
        
        # Analyze test files
        test_files = self._find_and_analyze_test_files(clone_path)

        # Build selector lookup (selector -> files that contain it)
        selector_lookup = self._build_selector_lookup(test_files)

        # Analyze dependencies
        dependency_analysis = self._analyze_dependencies(clone_path)

        # Analyze code patterns
        code_patterns = self._analyze_code_patterns(clone_path, test_files)

        return RepositoryAnalysisResult(
            repository_url=repo_url,
            branch=branch or 'main',
            commit_sha=commit_sha,
            repository_cloned=True,
            clone_path=str(clone_path),
            test_files=test_files,
            dependency_analysis=dependency_analysis,
            code_patterns=code_patterns,
            analysis_timestamp=analysis_timestamp,
            analysis_errors=analysis_errors,
            selector_lookup=selector_lookup
        )
    
    def _infer_repo_from_job(self, job_name: str) -> Optional[str]:
        """Infer repository URL from Jenkins job name"""
        job_lower = job_name.lower()
        
        for key, url in self.KNOWN_REPOS.items():
            if key in job_lower:
                self.logger.info(f"Inferred repository {url} from job {job_name}")
                return url
        
        return None
    
    def _clone_repository(self, repo_url: str, branch: Optional[str] = None) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
        """
        Clone a git repository.
        
        Returns:
            Tuple of (clone_path, commit_sha, error_message)
        """
        # Create a unique directory name from the repo URL
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        timestamp = int(time.time())
        clone_dir = self.base_path / f"{repo_name}_{timestamp}"
        
        try:
            # Build clone command (full clone for git history access)
            cmd = ['git', 'clone']

            if branch:
                cmd.extend(['--branch', branch])

            cmd.extend([repo_url, str(clone_dir)])
            
            self.logger.info(f"Cloning repository: {repo_url}")
            self.logger.debug(f"Clone command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                error_msg = f"Git clone failed: {result.stderr}"
                self.logger.error(error_msg)
                return None, None, error_msg
            
            # Get commit SHA
            commit_sha = self._get_head_commit(clone_dir)
            
            self.logger.info(f"Repository cloned to: {clone_dir}")
            self.logger.info(f"Commit SHA: {commit_sha}")
            
            return clone_dir, commit_sha, None
            
        except subprocess.TimeoutExpired:
            error_msg = "Git clone timed out after 120s"
            self.logger.error(error_msg)
            return None, None, error_msg
        except Exception as e:
            error_msg = f"Git clone error: {str(e)}"
            self.logger.error(error_msg)
            return None, None, error_msg
    
    def _get_head_commit(self, repo_path: Path) -> Optional[str]:
        """Get the HEAD commit SHA"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            
        except Exception:
            pass
        
        return None
    
    def _find_and_analyze_test_files(self, repo_path: Path) -> List[TestFileInfo]:
        """Find and analyze test files in the repository"""
        test_files = []
        
        # Walk through all files
        for root, dirs, files in os.walk(repo_path):
            # Skip node_modules and other irrelevant directories
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', 'dist', 'build', '__pycache__', '.venv']]
            
            for filename in files:
                file_path = Path(root) / filename
                relative_path = file_path.relative_to(repo_path)
                
                # Check if this is a test file
                framework = self._detect_test_framework(str(relative_path))
                
                if framework:
                    # Analyze the test file
                    test_count, selectors = self._analyze_test_file(file_path, framework)
                    
                    test_files.append(TestFileInfo(
                        path=str(relative_path),
                        test_framework=framework,
                        test_count=test_count,
                        selectors=selectors
                    ))
        
        self.logger.info(f"Found {len(test_files)} test files")
        return test_files
    
    def _detect_test_framework(self, file_path: str) -> Optional[str]:
        """Detect which test framework a file belongs to"""
        for framework, patterns in self.TEST_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, file_path, re.IGNORECASE):
                    return framework
        
        return None
    
    def _analyze_test_file(self, file_path: Path, framework: str) -> Tuple[int, List[str]]:
        """Analyze a test file for test count and selectors"""
        test_count = 0
        selectors = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Count tests based on framework
            if framework in ['cypress', 'jest', 'playwright']:
                # JavaScript/TypeScript test patterns
                test_patterns = [
                    r'\bit\s*\(',
                    r'\btest\s*\(',
                    r'\bdescribe\s*\(',
                    r'\bcontext\s*\(',
                ]
                
                for pattern in test_patterns:
                    test_count += len(re.findall(pattern, content))
                    
            elif framework == 'pytest':
                # Python test patterns
                test_patterns = [
                    r'\bdef\s+test_\w+\s*\(',
                    r'\bclass\s+Test\w+\s*:',
                ]
                
                for pattern in test_patterns:
                    test_count += len(re.findall(pattern, content))
            
            # Find selectors
            for pattern in self.SELECTOR_PATTERNS:
                matches = re.findall(pattern, content)
                selectors.extend(matches)
            
            # Remove duplicates
            selectors = list(set(selectors))
            
        except Exception as e:
            self.logger.debug(f"Error analyzing {file_path}: {e}")
        
        return test_count, selectors[:50]  # Limit to 50 unique selectors
    
    def _analyze_dependencies(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze project dependencies"""
        dependencies = {
            'framework': None,
            'version': None,
            'dependencies': [],
            'dev_dependencies': [],
            'healthy': True
        }
        
        # Check for package.json (Node.js projects)
        package_json = repo_path / 'package.json'
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    pkg = json.load(f)
                
                deps = pkg.get('dependencies', {})
                dev_deps = pkg.get('devDependencies', {})
                
                # Detect test framework
                if 'cypress' in deps or 'cypress' in dev_deps:
                    dependencies['framework'] = 'cypress'
                    dependencies['version'] = deps.get('cypress') or dev_deps.get('cypress')
                elif '@playwright/test' in deps or '@playwright/test' in dev_deps:
                    dependencies['framework'] = 'playwright'
                    dependencies['version'] = deps.get('@playwright/test') or dev_deps.get('@playwright/test')
                elif 'jest' in deps or 'jest' in dev_deps:
                    dependencies['framework'] = 'jest'
                    dependencies['version'] = deps.get('jest') or dev_deps.get('jest')
                
                # Extract key dependencies
                for name, version in deps.items():
                    dependencies['dependencies'].append(
                        asdict(DependencyInfo(name=name, version=version, is_dev=False))
                    )
                
                for name, version in dev_deps.items():
                    dependencies['dev_dependencies'].append(
                        asdict(DependencyInfo(name=name, version=version, is_dev=True))
                    )
                    
            except Exception as e:
                self.logger.warning(f"Error reading package.json: {e}")
                dependencies['healthy'] = False
        
        # Check for requirements.txt (Python projects)
        requirements = repo_path / 'requirements.txt'
        if requirements.exists():
            try:
                with open(requirements, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Parse dependency
                            match = re.match(r'^([a-zA-Z0-9_-]+)(?:[=<>]+(.+))?$', line)
                            if match:
                                name = match.group(1)
                                version = match.group(2) or 'latest'
                                
                                dependencies['dependencies'].append(
                                    asdict(DependencyInfo(name=name, version=version, is_dev=False))
                                )
                                
                                # Detect pytest
                                if name == 'pytest':
                                    dependencies['framework'] = 'pytest'
                                    dependencies['version'] = version
                                    
            except Exception as e:
                self.logger.warning(f"Error reading requirements.txt: {e}")
                dependencies['healthy'] = False
        
        return dependencies
    
    def _analyze_code_patterns(self, repo_path: Path, test_files: List[TestFileInfo]) -> Dict[str, Any]:
        """Analyze code patterns across test files"""
        patterns = {
            'selector_patterns': [],
            'wait_patterns': [],
            'assertion_patterns': [],
            'command_patterns': [],
            'page_object_usage': False,
            'fixtures_usage': False
        }
        
        # Aggregate selectors from test files
        all_selectors = []
        for tf in test_files:
            all_selectors.extend(tf.selectors)
        
        # Categorize selectors
        selector_types = {
            'data-test': 0,
            'data-cy': 0,
            'data-testid': 0,
            'class': 0,
            'id': 0,
            'other': 0
        }
        
        for selector in all_selectors:
            if 'data-test' in selector:
                selector_types['data-test'] += 1
            elif 'data-cy' in selector:
                selector_types['data-cy'] += 1
            elif 'data-testid' in selector:
                selector_types['data-testid'] += 1
            elif selector.startswith('.'):
                selector_types['class'] += 1
            elif selector.startswith('#'):
                selector_types['id'] += 1
            else:
                selector_types['other'] += 1
        
        patterns['selector_patterns'] = [
            {'type': k, 'count': v} for k, v in selector_types.items() if v > 0
        ]
        
        # Check for page objects
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git']]
            
            for dirname in dirs:
                if 'page' in dirname.lower() or 'pages' in dirname.lower():
                    patterns['page_object_usage'] = True
                    break
            
            for filename in files:
                if 'page' in filename.lower() and filename.endswith(('.js', '.ts', '.py')):
                    patterns['page_object_usage'] = True
                    break
        
        # Check for fixtures
        fixtures_dirs = ['fixtures', 'fixture', 'test-data', 'testdata']
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in ['node_modules', '.git']]
            
            for dirname in dirs:
                if dirname.lower() in fixtures_dirs:
                    patterns['fixtures_usage'] = True
                    break
        
        return patterns
    
    def cleanup_repository(self, clone_path: str):
        """Remove a cloned repository to free disk space"""
        try:
            if os.path.exists(clone_path):
                shutil.rmtree(clone_path)
                self.logger.info(f"Cleaned up repository: {clone_path}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup {clone_path}: {e}")
    
    def cleanup_all(self):
        """Remove all cloned repositories"""
        try:
            for item in self.base_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
            self.logger.info("Cleaned up all repositories")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup all repositories: {e}")

    def _build_selector_lookup(self, test_files: List[TestFileInfo]) -> Dict[str, List[str]]:
        """
        Build a lookup table mapping selectors to the files that contain them.

        Args:
            test_files: List of analyzed test files

        Returns:
            Dict mapping selector string to list of file paths
        """
        lookup = {}

        for tf in test_files:
            for selector in tf.selectors:
                if selector not in lookup:
                    lookup[selector] = []
                if tf.path not in lookup[selector]:
                    lookup[selector].append(tf.path)

        self.logger.info(f"Built selector lookup with {len(lookup)} unique selectors")
        return lookup

    def get_selector_history(
        self, repo_path: Path, selector: str, file_path: Optional[str] = None
    ) -> Optional[SelectorHistory]:
        """
        Get git history for a specific selector using git log -S.

        Args:
            repo_path: Path to the cloned repository
            selector: The selector string to search for
            file_path: Optional specific file to search in

        Returns:
            SelectorHistory with last modification info, or None if not found
        """
        try:
            cmd = [
                'git', 'log', '-1',
                '--format=%H|%ad|%s',
                '--date=iso',
                '-S', selector
            ]

            if file_path:
                cmd.extend(['--', file_path])

            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|', 2)
                if len(parts) >= 3:
                    commit_sha = parts[0]
                    date_str = parts[1]
                    message = parts[2]

                    # Calculate days since modified
                    days_ago = None
                    try:
                        from datetime import datetime
                        commit_date = datetime.fromisoformat(date_str.replace(' ', 'T').split('+')[0])
                        days_ago = (datetime.now() - commit_date).days
                    except Exception:
                        pass

                    return SelectorHistory(
                        selector=selector,
                        file_path=file_path or "",
                        last_modified_date=date_str,
                        last_commit_sha=commit_sha,
                        last_commit_message=message,
                        days_since_modified=days_ago
                    )

        except subprocess.TimeoutExpired:
            self.logger.warning(f"Git log timed out for selector: {selector}")
        except Exception as e:
            self.logger.debug(f"Error getting selector history: {e}")

        return None

    def get_file_content_around_line(
        self, repo_path: Path, file_path: str, line_number: int, context_lines: int = 20
    ) -> Optional[str]:
        """
        Extract file content around a specific line number.

        Args:
            repo_path: Path to the cloned repository
            file_path: Relative path to the file
            line_number: The line number to center on
            context_lines: Number of lines before and after to include

        Returns:
            String with the content, or None if file not found
        """
        full_path = repo_path / file_path

        if not full_path.exists():
            return None

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)

            # Build content with line numbers
            content_lines = []
            for i, line in enumerate(lines[start:end], start=start + 1):
                marker = '>>>' if i == line_number else '   '
                content_lines.append(f"{marker} {i:4d}: {line.rstrip()}")

            return '\n'.join(content_lines)

        except Exception as e:
            self.logger.debug(f"Error reading file {file_path}: {e}")
            return None

    def resolve_imports(self, repo_path: Path, file_path: str) -> List[str]:
        """
        Trace imports in a JavaScript/TypeScript file to find selector definitions.

        Args:
            repo_path: Path to the cloned repository
            file_path: Relative path to the file

        Returns:
            List of resolved import paths
        """
        full_path = repo_path / file_path
        import_chain = []

        if not full_path.exists():
            return import_chain

        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Match import patterns
            import_patterns = [
                r"import\s+\{[^}]+\}\s+from\s+['\"]([^'\"]+)['\"]",
                r"import\s+\*\s+as\s+\w+\s+from\s+['\"]([^'\"]+)['\"]",
                r"import\s+\w+\s+from\s+['\"]([^'\"]+)['\"]",
                r"const\s+\{[^}]+\}\s*=\s*require\(['\"]([^'\"]+)['\"]\)",
                r"require\(['\"]([^'\"]+)['\"]\)",
            ]

            for pattern in import_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Resolve relative paths
                    if match.startswith('.'):
                        base_dir = Path(file_path).parent
                        resolved = str((base_dir / match).resolve())
                        # Normalize and make relative
                        resolved = resolved.replace(str(repo_path) + '/', '')
                        import_chain.append(resolved)
                    else:
                        # External module or absolute path
                        import_chain.append(match)

        except Exception as e:
            self.logger.debug(f"Error resolving imports for {file_path}: {e}")

        return import_chain

    def get_targeted_evidence(
        self,
        repo_path: Path,
        failing_file: str,
        failing_line: int,
        failing_selector: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get targeted evidence for a specific failure point.

        Args:
            repo_path: Path to the cloned repository
            failing_file: File where failure occurred
            failing_line: Line number of failure
            failing_selector: Optional failing selector to look up

        Returns:
            Dict with file content, imports, and selector history
        """
        evidence = {
            'file_content': None,
            'imports': [],
            'selector_found': None,
            'selector_files': [],
            'selector_history': None,
        }

        # Get file content around failure
        evidence['file_content'] = self.get_file_content_around_line(
            repo_path, failing_file, failing_line
        )

        # Resolve imports
        evidence['imports'] = self.resolve_imports(repo_path, failing_file)

        # Check selector if provided
        if failing_selector:
            # Search for selector in all test files
            for root, dirs, files in os.walk(repo_path):
                dirs[:] = [d for d in dirs if d not in ['node_modules', '.git']]
                for filename in files:
                    if filename.endswith(('.js', '.ts', '.jsx', '.tsx')):
                        file_full_path = Path(root) / filename
                        try:
                            with open(file_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                if failing_selector in f.read():
                                    rel_path = str(file_full_path.relative_to(repo_path))
                                    evidence['selector_files'].append(rel_path)
                        except Exception:
                            pass

            evidence['selector_found'] = len(evidence['selector_files']) > 0

            # Get git history for selector
            history = self.get_selector_history(repo_path, failing_selector)
            if history:
                evidence['selector_history'] = asdict(history)

        return evidence

    def to_dict(self, result: RepositoryAnalysisResult) -> Dict[str, Any]:
        """Convert result to dictionary for serialization"""
        return {
            'repository_url': result.repository_url,
            'branch': result.branch,
            'commit_sha': result.commit_sha,
            'repository_cloned': result.repository_cloned,
            'clone_path': result.clone_path,
            'test_files': [asdict(tf) for tf in result.test_files],
            'dependency_analysis': result.dependency_analysis,
            'code_patterns': result.code_patterns,
            'analysis_timestamp': result.analysis_timestamp,
            'analysis_errors': result.analysis_errors,
            'selector_lookup': result.selector_lookup,
            'selector_history': result.selector_history,
            'file_contents': result.file_contents,
        }
