"""
Schema definitions for z-stream-analysis.

This module provides JSON schemas and templates for validating
AI-generated analysis results and multi-file data structures.
"""

from pathlib import Path

SCHEMA_DIR = Path(__file__).parent
ANALYSIS_RESULTS_SCHEMA = SCHEMA_DIR / 'analysis_results_schema.json'
ANALYSIS_RESULTS_TEMPLATE = SCHEMA_DIR / 'analysis_results_template.json'
EVIDENCE_PACKAGE_SCHEMA = SCHEMA_DIR / 'evidence_package_schema.json'
MANIFEST_SCHEMA = SCHEMA_DIR / 'manifest_schema.json'

__all__ = [
    'SCHEMA_DIR',
    'ANALYSIS_RESULTS_SCHEMA',
    'ANALYSIS_RESULTS_TEMPLATE',
    'EVIDENCE_PACKAGE_SCHEMA',
    'MANIFEST_SCHEMA'
]
