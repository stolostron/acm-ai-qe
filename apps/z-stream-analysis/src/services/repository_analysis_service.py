#!/usr/bin/env python3
"""
Repository Analysis Service
Real git clone and repository file analysis for test automation codebases

Usage:
    Clones repositories for AI to have full access during analysis.
    Uses git for cloning and file access.
"""

import logging
import os
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Import centralized configuration
from .shared_utils import REPOS, TIMEOUTS, THRESHOLDS


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
    Real git clone for AI full access
    """

    # Known test automation repositories - use centralized config
    # Can be overridden via Z_STREAM_AUTOMATION_REPOS environment variable
    @property
    def KNOWN_REPOS(self) -> Dict[str, str]:
        return REPOS.KNOWN_REPOS

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize Repository Analysis Service.

        Args:
            base_path: Base directory for cloning repositories
                      Default: /tmp/z-stream-repos
        """
        self.logger = logging.getLogger(__name__)
        default_base = os.environ.get('Z_STREAM_REPO_BASE_PATH', '/tmp/z-stream-repos')
        self.base_path = Path(base_path or default_base)

        # Create base directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Repository base path: {self.base_path}")

    def _infer_repo_from_job(self, job_name: str) -> Optional[str]:
        """Infer repository URL from Jenkins job name"""
        job_lower = job_name.lower()

        for key, url in self.KNOWN_REPOS.items():
            if key in job_lower:
                self.logger.info(f"Inferred repository {url} from job {job_name}")
                return url

        return None

    def _get_head_commit(self, repo_path: Path) -> Optional[str]:
        """Get the HEAD commit SHA"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.DEFAULT_COMMAND
            )

            if result.returncode == 0:
                return result.stdout.strip()

        except Exception:
            pass

        return None

    def clone_to(
        self,
        repo_url: str,
        branch: Optional[str],
        target_path: Path
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Clone a repository to a specific target path.

        This method clones the repository to a persistent location (e.g., runs/<dir>/repos/)
        instead of /tmp, allowing AI to have full access to the repo during analysis.

        Args:
            repo_url: Git repository URL
            branch: Branch to checkout (e.g., 'release-2.15')
            target_path: Directory to clone into (will be created if doesn't exist)

        Returns:
            Tuple of (success, commit_sha, error_message)
        """
        try:
            # Create target directory if needed
            target_path.mkdir(parents=True, exist_ok=True)

            # Build clone command (full clone for git history access)
            cmd = ['git', 'clone']

            if branch:
                cmd.extend(['--branch', branch])

            cmd.extend([repo_url, str(target_path)])

            self.logger.info(f"Cloning repository to: {target_path}")
            self.logger.debug(f"Clone command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.GIT_CLONE
            )

            if result.returncode != 0:
                # Check if directory already has content (target exists)
                if target_path.exists() and list(target_path.iterdir()):
                    # Try cloning into empty temp dir and moving
                    error_msg = f"Target directory not empty: {target_path}"
                    self.logger.error(error_msg)
                    return False, None, error_msg

                error_msg = f"Git clone failed: {result.stderr}"
                self.logger.error(error_msg)
                return False, None, error_msg

            # Get commit SHA
            commit_sha = self._get_head_commit(target_path)

            self.logger.info(f"Repository cloned successfully to: {target_path}")
            self.logger.info(f"Commit SHA: {commit_sha}")

            return True, commit_sha, None

        except subprocess.TimeoutExpired:
            error_msg = "Git clone timed out after 180s"
            self.logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Git clone error: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg

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
                timeout=TIMEOUTS.GIT_LOG
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
