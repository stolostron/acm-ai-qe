#!/usr/bin/env python3
"""
Enhanced Logging Manager - Separate Logs from Reports
====================================================

Architecture:
- runs/{JIRA_ID}/{TIMESTAMP}/     -> Reports only (Test-Cases.md, Complete-Analysis.md)
- .claude/logs/executions/        -> All comprehensive logs preserved permanently

This ensures:
1. Clean reports delivery (no clutter)
2. Complete log preservation (debugging, analysis)
3. Historical tracking (all past executions)
4. Proper separation of concerns
"""

import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class EnhancedLoggingManager:
    """
    Enhanced logging manager that separates reports from comprehensive logs
    """
    
    def __init__(self, framework_root: str = None):
        self.framework_root = Path(framework_root or self._find_framework_root())
        self.runs_dir = self.framework_root / "runs"
        self.logs_dir = self.framework_root / ".claude" / "logs" / "executions"
        
        # Ensure directories exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
    def _find_framework_root(self) -> Path:
        """Find framework root directory"""
        current = Path(__file__).parent
        while current != current.parent:
            if (current / 'CLAUDE.md').exists():
                return current
            current = current.parent
        return Path.cwd()
    
    def initialize_execution_logging(self, jira_id: str, run_timestamp: str) -> Dict[str, Path]:
        """
        Initialize logging directories for a new execution
        
        Returns:
            Dict with paths to reports and logs directories
        """
        # Reports directory (clean output)
        reports_dir = self.runs_dir / jira_id / f"{jira_id}-{run_timestamp}"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Comprehensive logs directory
        logs_dir = self.logs_dir / jira_id / run_timestamp
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organized logging
        subdirs = [
            "agents",
            "coordination", 
            "tools",
            "phases",
            "environment",
            "performance",
            "validation",
            "context"
        ]
        
        for subdir in subdirs:
            (logs_dir / subdir).mkdir(exist_ok=True)
        
        logger.info(f"Enhanced logging initialized for {jira_id}-{run_timestamp}")
        logger.info(f"Reports directory: {reports_dir}")
        logger.info(f"Logs directory: {logs_dir}")
        
        return {
            "reports_dir": reports_dir,
            "logs_dir": logs_dir,
            "agents_dir": logs_dir / "agents",
            "coordination_dir": logs_dir / "coordination",
            "tools_dir": logs_dir / "tools", 
            "phases_dir": logs_dir / "phases",
            "environment_dir": logs_dir / "environment",
            "performance_dir": logs_dir / "performance",
            "validation_dir": logs_dir / "validation",
            "context_dir": logs_dir / "context"
        }
    
    def organize_execution_logs(self, run_directory: str, jira_id: str, run_timestamp: str) -> Dict[str, Any]:
        """
        Organize logs from a completed execution
        
        Args:
            run_directory: Source directory with mixed files
            jira_id: JIRA ticket ID
            run_timestamp: Execution timestamp
        """
        run_path = Path(run_directory)
        if not run_path.exists():
            logger.warning(f"Run directory not found: {run_directory}")
            return {"success": False, "error": "Run directory not found"}
        
        # Initialize enhanced logging structure
        paths = self.initialize_execution_logging(jira_id, run_timestamp)
        
        # Statistics
        reports_moved = 0
        logs_preserved = 0
        temp_cleaned = 0
        
        try:
            # Process all files in the run directory
            for item in run_path.iterdir():
                if item.is_file():
                    # Essential reports - keep in runs directory
                    if item.name in ["Test-Cases.md", "Complete-Analysis.md"]:
                        dest = paths["reports_dir"] / item.name
                        if item != dest:  # Only move if different location
                            shutil.copy2(item, dest)
                            reports_moved += 1
                        logger.info(f"Report preserved: {item.name}")
                    
                    # Run metadata - keep in runs directory  
                    elif item.name in ["run-metadata.json", "execution-summary.json"]:
                        dest = paths["reports_dir"] / item.name
                        if item != dest:
                            shutil.copy2(item, dest)
                        logger.info(f"Metadata preserved: {item.name}")
                    
                    # Agent logs - move to comprehensive logs
                    elif "agent" in item.name.lower() and item.suffix in [".json", ".jsonl"]:
                        dest = paths["agents_dir"] / item.name
                        shutil.copy2(item, dest)
                        logs_preserved += 1
                        logger.info(f"Agent log preserved: {item.name}")
                    
                    # Tool execution logs
                    elif any(tool in item.name.lower() for tool in ["bash", "tool", "command", "api"]):
                        dest = paths["tools_dir"] / item.name
                        shutil.copy2(item, dest)
                        logs_preserved += 1
                        logger.info(f"Tool log preserved: {item.name}")
                    
                    # Coordination logs
                    elif any(coord in item.name.lower() for coord in ["coordination", "communication", "realtime"]):
                        dest = paths["coordination_dir"] / item.name
                        shutil.copy2(item, dest) 
                        logs_preserved += 1
                        logger.info(f"Coordination log preserved: {item.name}")
                    
                    # Phase logs
                    elif "phase" in item.name.lower():
                        dest = paths["phases_dir"] / item.name
                        shutil.copy2(item, dest)
                        logs_preserved += 1
                        logger.info(f"Phase log preserved: {item.name}")
                    
                    # Environment logs
                    elif "environment" in item.name.lower():
                        dest = paths["environment_dir"] / item.name
                        shutil.copy2(item, dest)
                        logs_preserved += 1
                        logger.info(f"Environment log preserved: {item.name}")
                    
                    # Performance logs
                    elif any(perf in item.name.lower() for perf in ["performance", "metrics", "timing"]):
                        dest = paths["performance_dir"] / item.name
                        shutil.copy2(item, dest)
                        logs_preserved += 1
                        logger.info(f"Performance log preserved: {item.name}")
                    
                    # Context logs
                    elif "context" in item.name.lower():
                        dest = paths["context_dir"] / item.name
                        shutil.copy2(item, dest)
                        logs_preserved += 1
                        logger.info(f"Context log preserved: {item.name}")
                    
                    # Validation logs
                    elif any(val in item.name.lower() for val in ["validation", "enforcement", "compliance"]):
                        dest = paths["validation_dir"] / item.name
                        shutil.copy2(item, dest)
                        logs_preserved += 1
                        logger.info(f"Validation log preserved: {item.name}")
                    
                    # Framework master logs
                    elif any(master in item.name.lower() for master in ["master", "comprehensive", "framework"]):
                        dest = paths["logs_dir"] / item.name
                        shutil.copy2(item, dest)
                        logs_preserved += 1
                        logger.info(f"Master log preserved: {item.name}")
                    
                    # Temporary files - mark for cleanup
                    elif any(temp in item.name.lower() for temp in ["temp", "tmp", "cache", "intermediate"]):
                        temp_cleaned += 1
                        logger.info(f"Temp file marked for cleanup: {item.name}")
                    
                    # Unknown files - preserve in logs for safety
                    else:
                        dest = paths["logs_dir"] / item.name
                        shutil.copy2(item, dest)
                        logs_preserved += 1
                        logger.info(f"Unknown file preserved in logs: {item.name}")
                
                # Handle subdirectories
                elif item.is_dir():
                    # Recursively organize subdirectories
                    self._organize_subdirectory(item, paths["logs_dir"] / item.name)
                    logs_preserved += 1
            
            # Create execution summary
            summary = {
                "jira_id": jira_id,
                "run_timestamp": run_timestamp,
                "execution_time": datetime.now().isoformat(),
                "directories": {
                    "reports": str(paths["reports_dir"]),
                    "comprehensive_logs": str(paths["logs_dir"])
                },
                "statistics": {
                    "reports_moved": reports_moved,
                    "logs_preserved": logs_preserved,
                    "temp_cleaned": temp_cleaned
                },
                "architecture": "enhanced_separation_v1.0"
            }
            
            # Save summary in both locations
            summary_file = paths["reports_dir"] / "logging-summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            summary_file_logs = paths["logs_dir"] / "execution-summary.json"
            with open(summary_file_logs, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Enhanced logging organization complete: {reports_moved} reports, {logs_preserved} logs preserved")
            
            return {
                "success": True,
                "summary": summary,
                "paths": {k: str(v) for k, v in paths.items()}
            }
            
        except Exception as e:
            logger.error(f"Enhanced logging organization failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "partial_results": {
                    "reports_moved": reports_moved,
                    "logs_preserved": logs_preserved
                }
            }
    
    def _organize_subdirectory(self, source_dir: Path, dest_dir: Path):
        """Recursively organize subdirectories"""
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        for item in source_dir.iterdir():
            dest_item = dest_dir / item.name
            if item.is_file():
                shutil.copy2(item, dest_item)
            elif item.is_dir():
                self._organize_subdirectory(item, dest_item)
    
    def enhanced_cleanup_with_preservation(self, run_directory: str) -> Dict[str, Any]:
        """
        Enhanced Phase 5 cleanup that preserves logs while cleaning reports directory
        
        This replaces the old cleanup that deleted everything
        """
        run_path = Path(run_directory)
        if not run_path.exists():
            return {"success": False, "error": "Run directory not found"}
        
        # Extract JIRA ID and timestamp from directory name
        dir_name = run_path.name
        if "-" in dir_name:
            parts = dir_name.split("-")
            if len(parts) >= 3:
                jira_id = parts[0]
                # Handle both timestamp formats: YYYYMMDD-HHMMSS and YYYYMMDD_HHMMSS
                timestamp_part = "-".join(parts[1:]) if len(parts) == 3 else "-".join(parts[1:3])
                
                # First organize and preserve all logs
                organize_result = self.organize_execution_logs(str(run_path), jira_id, timestamp_part)
                
                if organize_result["success"]:
                    # Now clean temporary files from runs directory (keeping only reports)
                    reports_to_keep = ["Test-Cases.md", "Complete-Analysis.md", "run-metadata.json", "logging-summary.json"]
                    temp_files_removed = 0
                    
                    for item in run_path.iterdir():
                        if item.is_file() and item.name not in reports_to_keep:
                            try:
                                item.unlink()
                                temp_files_removed += 1
                                logger.info(f"Cleaned temp file: {item.name}")
                            except Exception as e:
                                logger.warning(f"Could not remove {item.name}: {e}")
                        elif item.is_dir():
                            try:
                                shutil.rmtree(item)
                                temp_files_removed += 1
                                logger.info(f"Cleaned temp directory: {item.name}")
                            except Exception as e:
                                logger.warning(f"Could not remove directory {item.name}: {e}")
                    
                    summary = organize_result["summary"]
                    summary["cleanup"] = {
                        "temp_files_removed": temp_files_removed,
                        "reports_preserved": len(reports_to_keep),
                        "cleanup_completed": True
                    }
                    
                    return {
                        "success": True,
                        "summary": f"Enhanced cleanup: {summary['statistics']['logs_preserved']} logs preserved, {temp_files_removed} temp files cleaned",
                        "details": summary,
                        "architecture": "enhanced_separation_with_preservation"
                    }
                else:
                    return organize_result
        
        return {"success": False, "error": "Could not parse directory name for JIRA ID and timestamp"}
    
    def get_execution_history(self, jira_id: str = None) -> Dict[str, Any]:
        """Get history of all executions with comprehensive logs"""
        history = []
        
        search_dir = self.logs_dir / jira_id if jira_id else self.logs_dir
        
        if search_dir.exists():
            for jira_dir in search_dir.iterdir():
                if jira_dir.is_dir():
                    current_jira = jira_dir.name if jira_id else jira_dir.name
                    
                    execution_dir = jira_dir if jira_id else jira_dir
                    for run_dir in execution_dir.iterdir():
                        if run_dir.is_dir():
                            timestamp = run_dir.name if jira_id else run_dir.name
                            
                            # Check for execution summary
                            summary_file = run_dir / "execution-summary.json"
                            if summary_file.exists():
                                try:
                                    with open(summary_file, 'r') as f:
                                        summary = json.load(f)
                                    history.append(summary)
                                except Exception as e:
                                    logger.warning(f"Could not read summary for {current_jira}/{timestamp}: {e}")
                            else:
                                # Create basic entry
                                history.append({
                                    "jira_id": current_jira,
                                    "run_timestamp": timestamp,
                                    "logs_directory": str(run_dir),
                                    "has_comprehensive_logs": True
                                })
        
        return {
            "total_executions": len(history),
            "executions": sorted(history, key=lambda x: x.get("run_timestamp", ""), reverse=True),
            "logs_directory": str(self.logs_dir)
        }

# Global instance
enhanced_logging_manager = EnhancedLoggingManager()

# Convenience functions
def organize_execution_logs(run_directory: str, jira_id: str, run_timestamp: str) -> Dict[str, Any]:
    """Organize logs from execution with enhanced separation"""
    return enhanced_logging_manager.organize_execution_logs(run_directory, jira_id, run_timestamp)

def enhanced_cleanup_with_preservation(run_directory: str) -> Dict[str, Any]:
    """Enhanced cleanup that preserves comprehensive logs"""
    return enhanced_logging_manager.enhanced_cleanup_with_preservation(run_directory)

def get_execution_history(jira_id: str = None) -> Dict[str, Any]:
    """Get execution history with comprehensive logs"""
    return enhanced_logging_manager.get_execution_history(jira_id)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Logging Manager")
    parser.add_argument("--organize", type=str, help="Organize logs for run directory")
    parser.add_argument("--jira-id", type=str, help="JIRA ticket ID")
    parser.add_argument("--timestamp", type=str, help="Run timestamp")
    parser.add_argument("--cleanup", type=str, help="Enhanced cleanup for run directory")
    parser.add_argument("--history", action="store_true", help="Show execution history")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    if args.organize and args.jira_id and args.timestamp:
        result = organize_execution_logs(args.organize, args.jira_id, args.timestamp)
        print(json.dumps(result, indent=2))
    elif args.cleanup:
        result = enhanced_cleanup_with_preservation(args.cleanup)
        print(json.dumps(result, indent=2))
    elif args.history:
        result = get_execution_history(args.jira_id)
        print(json.dumps(result, indent=2))
    else:
        print("Enhanced Logging Manager - Use --help for options")