#!/usr/bin/env python3
"""
Scripts Package
Deterministic scripts for data gathering and report generation.

These scripts handle mechanical tasks while AI handles analytical reasoning.

Modules:
    gather: Data gathering from Jenkins, environment, and repository
    report: Report generation in various formats
"""


def __getattr__(name):
    """Lazy imports to avoid RuntimeWarning when using python -m."""
    if name in ('DataGatherer', 'gather_all_data'):
        from .gather import DataGatherer, gather_all_data
        return DataGatherer if name == 'DataGatherer' else gather_all_data
    if name in ('ReportFormatter', 'format_reports'):
        from .report import ReportFormatter, format_reports
        return ReportFormatter if name == 'ReportFormatter' else format_reports
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'DataGatherer',
    'gather_all_data',
    'ReportFormatter',
    'format_reports',
]
