#!/usr/bin/env python3
"""Scan knowledge DB files for staleness based on last_verified date and acm_version.

Usage:
    python3 check-staleness.py [--threshold-days 30] [--target-version 5.0] [--json]

Exits with code 1 if any files are stale, 0 if all are fresh.
"""

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

KB_ROOT = Path(__file__).resolve().parent.parent

def parse_frontmatter(filepath: Path) -> dict:
    """Extract YAML frontmatter fields from a markdown file."""
    content = filepath.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return {"_has_frontmatter": False}
    
    end_idx = content.index("\n---", 4)
    fm_block = content[4:end_idx]
    
    result = {"_has_frontmatter": True}
    for line in fm_block.split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith("-") and not line.startswith("#"):
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key in ("type", "subsystem", "acm_version", "last_verified"):
                result[key] = val
    return result

def check_staleness(threshold_days: int, target_version: str | None) -> list[dict]:
    """Check all knowledge files for staleness."""
    today = date.today()
    threshold_date = today - timedelta(days=threshold_days)
    stale_files = []
    
    for md_file in sorted(KB_ROOT.rglob("*.md")):
        if md_file.name in ("README.md", ".gitkeep"):
            continue
        if "scripts/" in str(md_file.relative_to(KB_ROOT)):
            continue
            
        rel_path = str(md_file.relative_to(KB_ROOT))
        fm = parse_frontmatter(md_file)
        
        if not fm.get("_has_frontmatter"):
            stale_files.append({
                "file": rel_path,
                "reason": "missing_frontmatter",
                "detail": "No YAML frontmatter found",
            })
            continue
        
        last_verified = fm.get("last_verified")
        if last_verified:
            try:
                verified_date = date.fromisoformat(last_verified)
                if verified_date < threshold_date:
                    age_days = (today - verified_date).days
                    stale_files.append({
                        "file": rel_path,
                        "reason": "date_stale",
                        "detail": f"Last verified {age_days} days ago ({last_verified})",
                        "last_verified": last_verified,
                        "age_days": age_days,
                    })
            except ValueError:
                stale_files.append({
                    "file": rel_path,
                    "reason": "invalid_date",
                    "detail": f"Invalid last_verified date: {last_verified}",
                })
        else:
            stale_files.append({
                "file": rel_path,
                "reason": "missing_date",
                "detail": "No last_verified field in frontmatter",
            })
        
        if target_version:
            file_version = fm.get("acm_version", "")
            if file_version and file_version != target_version:
                stale_files.append({
                    "file": rel_path,
                    "reason": "version_stale",
                    "detail": f"Verified against ACM {file_version}, current target is {target_version}",
                    "acm_version": file_version,
                    "target_version": target_version,
                })
    
    return stale_files

def main():
    parser = argparse.ArgumentParser(description="Check knowledge DB for stale files")
    parser.add_argument("--threshold-days", type=int, default=30,
                        help="Flag files older than this many days (default: 30)")
    parser.add_argument("--target-version", type=str, default=None,
                        help="Flag files verified against a different ACM version")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of human-readable text")
    args = parser.parse_args()
    
    stale_files = check_staleness(args.threshold_days, args.target_version)
    
    if args.json:
        print(json.dumps({"stale_count": len(stale_files), "files": stale_files}, indent=2))
    else:
        if not stale_files:
            print(f"All knowledge files are fresh (threshold: {args.threshold_days} days)")
            sys.exit(0)
        
        by_reason = {}
        for sf in stale_files:
            reason = sf["reason"]
            by_reason.setdefault(reason, []).append(sf)
        
        print(f"Staleness Report ({len(stale_files)} issues found)")
        print(f"Threshold: {args.threshold_days} days | Target version: {args.target_version or 'not set'}")
        print("=" * 60)
        
        for reason, files in sorted(by_reason.items()):
            labels = {
                "missing_frontmatter": "Missing Frontmatter",
                "date_stale": "Date Stale",
                "version_stale": "Version Stale",
                "missing_date": "Missing Date",
                "invalid_date": "Invalid Date",
            }
            print(f"\n{labels.get(reason, reason)} ({len(files)} files):")
            for sf in files:
                print(f"  - {sf['file']}: {sf['detail']}")
    
    sys.exit(1 if stale_files else 0)

if __name__ == "__main__":
    main()
