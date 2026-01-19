#!/usr/bin/env python3
"""
Stack Trace Parser Service

Parses JavaScript/TypeScript stack traces to extract structured information
including file paths, line numbers, and function names.

Handles various stack trace formats:
- Webpack paths: webpack://app/./cypress/file.js:181:11
- Node.js standard: at Context.eval (/path/file.js:123:45)
- Anonymous functions: at Object.<anonymous> (file.js:10:5)
- Async/await: at async Context.eval (file.ts:50:3)
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class StackFrame:
    """Represents a single frame in a stack trace."""
    file_path: str
    line_number: int
    column_number: Optional[int] = None
    function_name: Optional[str] = None
    is_test_file: bool = False
    is_framework_file: bool = False
    is_support_file: bool = False
    raw_line: str = ""

    def __post_init__(self):
        """Determine file type after initialization."""
        path_lower = self.file_path.lower()

        # Test file patterns
        test_patterns = [
            '/tests/', '/test/', '/spec/', '/specs/',
            '.spec.', '.test.', '.cy.', '_spec.', '_test.'
        ]
        self.is_test_file = any(p in path_lower for p in test_patterns)

        # Framework file patterns (node_modules, cypress internals)
        framework_patterns = [
            'node_modules/', 'cypress_runner', '__cypress',
            '/runner/', 'bluebird', 'promise'
        ]
        self.is_framework_file = any(p in path_lower for p in framework_patterns)

        # Support file patterns (commands, helpers, utilities)
        support_patterns = [
            '/support/', '/commands', '/helpers/', '/utils/',
            '/views/', '/pages/', '/fixtures/'
        ]
        self.is_support_file = any(p in path_lower for p in support_patterns)


@dataclass
class ParsedStackTrace:
    """Complete parsed stack trace with all frames and metadata."""
    raw_trace: str
    frames: List[StackFrame] = field(default_factory=list)
    root_cause_frame: Optional[StackFrame] = None
    test_file_frame: Optional[StackFrame] = None
    support_file_frame: Optional[StackFrame] = None
    error_type: str = "Unknown"
    error_message: str = ""
    total_frames: int = 0
    user_code_frames: int = 0


class StackTraceParser:
    """
    Parser for JavaScript/TypeScript stack traces.

    Extracts structured information from various stack trace formats
    commonly seen in Cypress, Jest, and Node.js test failures.
    """

    # Regex patterns for different stack trace formats
    PATTERNS = [
        # Webpack paths: webpack://app/./cypress/file.js:181:11
        re.compile(
            r'webpack://[^/]+/\.?/?(?P<file>[^:]+):(?P<line>\d+)(?::(?P<col>\d+))?'
        ),

        # Standard Node.js: at functionName (/path/to/file.js:123:45)
        re.compile(
            r'at\s+(?P<func>[^\s(]+)\s+\((?P<file>[^:]+):(?P<line>\d+)(?::(?P<col>\d+))?\)'
        ),

        # Anonymous functions: at Object.<anonymous> (file.js:10:5)
        re.compile(
            r'at\s+(?P<func>Object\.<anonymous>|<anonymous>)\s+\((?P<file>[^:]+):(?P<line>\d+)(?::(?P<col>\d+))?\)'
        ),

        # Async functions: at async Context.eval (file.ts:50:3)
        re.compile(
            r'at\s+async\s+(?P<func>[^\s(]+)\s+\((?P<file>[^:]+):(?P<line>\d+)(?::(?P<col>\d+))?\)'
        ),

        # Simple format without function: at /path/to/file.js:123:45
        re.compile(
            r'at\s+(?P<file>/[^:]+):(?P<line>\d+)(?::(?P<col>\d+))?'
        ),

        # Cypress-specific: From Your Spec Code: at Context.eval (webpack://...)
        re.compile(
            r'From Your Spec Code:.*?(?P<file>[^:]+):(?P<line>\d+)(?::(?P<col>\d+))?'
        ),

        # Error location in parentheses: (cypress/views/file.js:181:11)
        re.compile(
            r'\((?P<file>cypress/[^:]+):(?P<line>\d+)(?::(?P<col>\d+))?\)'
        ),
    ]

    # Pattern to extract error type and message
    ERROR_PATTERN = re.compile(
        r'^(?P<type>[A-Za-z]+Error|Error):\s*(?P<message>.+?)(?:\n|$)',
        re.MULTILINE
    )

    # Alternative error patterns
    ALT_ERROR_PATTERNS = [
        re.compile(r'^(?P<type>AssertionError):\s*(?P<message>.+)', re.MULTILINE),
        re.compile(r'^(?P<type>CypressError):\s*(?P<message>.+)', re.MULTILINE),
        re.compile(r'^(?P<type>TimeoutError):\s*(?P<message>.+)', re.MULTILINE),
        re.compile(r'(?P<type>expected)\s+(?P<message>.+?to\s+.+)', re.IGNORECASE),
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse(self, stack_trace: str) -> ParsedStackTrace:
        """
        Parse a stack trace string into structured format.

        Args:
            stack_trace: Raw stack trace string

        Returns:
            ParsedStackTrace with extracted frames and metadata
        """
        if not stack_trace:
            return ParsedStackTrace(raw_trace="")

        result = ParsedStackTrace(raw_trace=stack_trace)

        # Extract error type and message
        result.error_type, result.error_message = self._extract_error_info(stack_trace)

        # Parse all frames
        result.frames = self._extract_frames(stack_trace)
        result.total_frames = len(result.frames)

        # Count user code frames (non-framework)
        result.user_code_frames = sum(
            1 for f in result.frames if not f.is_framework_file
        )

        # Identify key frames
        result.root_cause_frame = self._find_root_cause_frame(result.frames)
        result.test_file_frame = self._find_test_file_frame(result.frames)
        result.support_file_frame = self._find_support_file_frame(result.frames)

        return result

    def _extract_error_info(self, stack_trace: str) -> Tuple[str, str]:
        """Extract error type and message from stack trace."""
        # Try main pattern
        match = self.ERROR_PATTERN.search(stack_trace)
        if match:
            return match.group('type'), match.group('message').strip()

        # Try alternative patterns
        for pattern in self.ALT_ERROR_PATTERNS:
            match = pattern.search(stack_trace)
            if match:
                error_type = match.group('type')
                message = match.group('message').strip()
                # Normalize error type
                if error_type.lower() == 'expected':
                    error_type = 'AssertionError'
                return error_type, message

        # Try to extract from first line
        first_line = stack_trace.split('\n')[0].strip()
        if ':' in first_line:
            parts = first_line.split(':', 1)
            return parts[0].strip(), parts[1].strip() if len(parts) > 1 else ""

        return "Unknown", first_line

    def _extract_frames(self, stack_trace: str) -> List[StackFrame]:
        """Extract all stack frames from the trace."""
        frames = []
        seen_locations = set()  # Avoid duplicates

        for line in stack_trace.split('\n'):
            line = line.strip()
            if not line:
                continue

            frame = self._parse_line(line)
            if frame:
                # Create unique key for deduplication
                location_key = f"{frame.file_path}:{frame.line_number}"
                if location_key not in seen_locations:
                    seen_locations.add(location_key)
                    frames.append(frame)

        return frames

    def _parse_line(self, line: str) -> Optional[StackFrame]:
        """Parse a single line to extract stack frame info."""
        for pattern in self.PATTERNS:
            match = pattern.search(line)
            if match:
                groups = match.groupdict()

                file_path = self._normalize_path(groups.get('file', ''))
                if not file_path:
                    continue

                try:
                    line_num = int(groups.get('line', 0))
                except (ValueError, TypeError):
                    continue

                if line_num <= 0:
                    continue

                col_num = None
                if groups.get('col'):
                    try:
                        col_num = int(groups['col'])
                    except (ValueError, TypeError):
                        pass

                func_name = groups.get('func')
                if func_name:
                    func_name = self._clean_function_name(func_name)

                return StackFrame(
                    file_path=file_path,
                    line_number=line_num,
                    column_number=col_num,
                    function_name=func_name,
                    raw_line=line
                )

        return None

    def _normalize_path(self, path: str) -> str:
        """Normalize file path from various formats."""
        if not path:
            return ""

        # Remove webpack:// prefix
        if path.startswith('webpack://'):
            # webpack://app-name/./path/to/file.js -> path/to/file.js
            path = re.sub(r'^webpack://[^/]+/\.?/?', '', path)

        # Remove leading ./ or /
        path = re.sub(r'^\.?/', '', path)

        # Remove query strings
        path = re.sub(r'\?.*$', '', path)

        # Normalize slashes
        path = path.replace('\\', '/')

        return path.strip()

    def _clean_function_name(self, name: str) -> str:
        """Clean up function name."""
        if not name:
            return ""

        # Remove 'async ' prefix
        name = re.sub(r'^async\s+', '', name)

        # Clean up Object.<anonymous>
        if '<anonymous>' in name:
            return '<anonymous>'

        return name.strip()

    def _find_root_cause_frame(self, frames: List[StackFrame]) -> Optional[StackFrame]:
        """
        Find the most likely root cause frame.

        This is typically the first non-framework frame, preferring
        support/view files over test files (since errors often originate
        in helper methods).
        """
        # First, look for support/view files (page objects, helpers)
        for frame in frames:
            if frame.is_support_file and not frame.is_framework_file:
                return frame

        # Then, look for any non-framework file
        for frame in frames:
            if not frame.is_framework_file:
                return frame

        # Fall back to first frame
        return frames[0] if frames else None

    def _find_test_file_frame(self, frames: List[StackFrame]) -> Optional[StackFrame]:
        """Find the frame from the actual test file."""
        for frame in frames:
            if frame.is_test_file and not frame.is_framework_file:
                return frame
        return None

    def _find_support_file_frame(self, frames: List[StackFrame]) -> Optional[StackFrame]:
        """Find the frame from a support/view file."""
        for frame in frames:
            if frame.is_support_file and not frame.is_framework_file:
                return frame
        return None

    def extract_failing_selector(self, error_message: str) -> Optional[str]:
        """
        Extract the failing selector from an error message.

        Common patterns:
        - "Expected to find element: `#selector`, but never found it"
        - "Timed out retrying: cy.get('#selector')"
        - "Element not found: .class-name"
        """
        patterns = [
            # Cypress element not found
            re.compile(r"Expected to find element:\s*[`'\"]?([^`'\"]+)[`'\"]?"),
            re.compile(r"cy\.get\(['\"]([^'\"]+)['\"]\)"),
            re.compile(r"cy\.find\(['\"]([^'\"]+)['\"]\)"),

            # Generic element patterns
            re.compile(r"Element[^:]*:\s*[`'\"]?([#.][^`'\">\s]+)[`'\"]?"),
            re.compile(r"selector[^:]*:\s*[`'\"]?([^`'\"]+)[`'\"]?", re.IGNORECASE),

            # Quoted selectors
            re.compile(r"[`'\"]([#.][a-zA-Z][a-zA-Z0-9_-]*)[`'\"]"),
            re.compile(r"[`'\"](\[data-[^\]]+\])[`'\"]"),
        ]

        for pattern in patterns:
            match = pattern.search(error_message)
            if match:
                selector = match.group(1).strip()
                # Validate it looks like a selector
                if selector and (
                    selector.startswith('#') or
                    selector.startswith('.') or
                    selector.startswith('[') or
                    'data-' in selector
                ):
                    return selector

        return None

    def get_context_range(self, frame: StackFrame, context_lines: int = 20) -> Tuple[int, int]:
        """
        Get the line range to extract for context around a failure.

        Args:
            frame: The stack frame
            context_lines: Number of lines before and after

        Returns:
            Tuple of (start_line, end_line)
        """
        start = max(1, frame.line_number - context_lines)
        end = frame.line_number + context_lines
        return start, end


def parse_stack_trace(raw_trace: str) -> ParsedStackTrace:
    """Convenience function to parse a stack trace."""
    parser = StackTraceParser()
    return parser.parse(raw_trace)
