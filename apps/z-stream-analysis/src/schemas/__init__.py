"""
Schema definitions for z-stream-analysis.

This module provides JSON schemas and templates for validating
AI-generated analysis results and multi-file data structures.
"""

from pathlib import Path

SCHEMA_DIR = Path(__file__).parent
ANALYSIS_RESULTS_SCHEMA = SCHEMA_DIR / 'analysis_results_schema.json'
MANIFEST_SCHEMA = SCHEMA_DIR / 'manifest_schema.json'

__all__ = [
    'SCHEMA_DIR',
    'ANALYSIS_RESULTS_SCHEMA',
    'MANIFEST_SCHEMA'
]
