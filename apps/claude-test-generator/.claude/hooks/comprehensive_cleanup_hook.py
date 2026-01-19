#!/usr/bin/env python3
"""
Comprehensive Cleanup Hook
===========================

Cleanup hooks for temporary data removal that can be triggered:
1. After framework execution completion
2. Manually via command line
3. As part of CI/CD pipelines
4. On framework initialization to clean stale data

This hook system ensures that temporary data is always cleaned up,
regardless of how the framework is invoked.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir / '..' / 'ai-services'))

import sys
sys.path.append('../ai-services')
try:
    import sys
    import os
    # Try to import temp cleanup service with fallback paths
    try:
        ai_services_path = os.path.join(os.path.dirname(__file__), '..', 'ai-services')
        if ai_services_path not in sys.path:
            sys.path.append(ai_services_path)
        from temp_data_cleanup_service import ComprehensiveTempDataCleanupService
    except ImportError:
        sys.path.append('../ai-services')
        from temp_data_cleanup_service import ComprehensiveTempDataCleanupService
except ImportError:
    ComprehensiveTempDataCleanupService = None

# Import enhanced logging manager
from enhanced_logging_manager import enhanced_cleanup_with_preservation

logger = logging.getLogger(__name__)

class ComprehensiveCleanupHook:
    """
    Comprehensive cleanup hook system for automatic temporary data removal.
    """
    
    def __init__(self):
        self.cleanup_service = ComprehensiveTempDataCleanupService()
        self.framework_root = self._find_framework_root()
        
    def _find_framework_root(self) -> Path:
        """Find framework root directory"""
        current = Path(__file__).parent
        
        # Go up directory tree looking for framework indicators
        while current != current.parent:
            if (current / 'CLAUDE.md').exists() or (current / '.claude').exists():
                return current
            current = current.parent
        
        # Fallback to current working directory
        return Path.cwd()
    
    def post_execution_cleanup_hook(self, run_directory: str) -> Dict[str, Any]:
        """
        Hook: Enhanced cleanup with log preservation
        
        NEW ARCHITECTURE:
        - Preserves ALL logs in .claude/logs/executions/{JIRA_ID}/{TIMESTAMP}/
        - Keeps only essential reports in runs/{JIRA_ID}/{TIMESTAMP}/
        - Maintains complete historical tracking for debugging
        
        Args:
            run_directory: Directory of the completed run
            
        Returns:
            Dict with cleanup results
        """
        logger.info(f"🧹 ENHANCED POST-EXECUTION CLEANUP: Organizing logs and cleaning {run_directory}")
        
        try:
            # Use enhanced cleanup with log preservation
            result = enhanced_cleanup_with_preservation(run_directory)
            
            if result['success']:
                logger.info(f"✅ Enhanced cleanup completed: {result['summary']}")
                logger.info(f"📊 Reports in: runs directory")
                logger.info(f"🔍 Comprehensive logs in: .claude/logs/executions/")
            else:
                logger.warning(f"⚠️ Enhanced cleanup had issues: {result.get('error', 'Unknown')}")
                
                # Fallback to original cleanup if enhanced fails
                if self.cleanup_service and ComprehensiveTempDataCleanupService:
                    logger.info("🔄 Falling back to original cleanup...")
                    fallback_result = self.cleanup_service.execute_comprehensive_cleanup(run_directory)
                    return {
                        'success': fallback_result.get('success', False),
                        'enhanced_cleanup_error': result.get('error'),
                        'fallback_used': True,
                        'fallback_result': fallback_result
                    }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Enhanced cleanup hook failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'cleanup_statistics': {'files_removed': 0, 'directories_removed': 0, 'bytes_cleaned': 0}
            }
    
    def framework_initialization_cleanup_hook(self) -> Dict[str, Any]:
        """
        Hook: Clean stale temporary data on framework initialization
        
        This removes any leftover temporary data from previous runs,
        especially the temp_repos directory that may contain stale clones.
        
        Returns:
            Dict with cleanup results
        """
        logger.info("🧹 FRAMEWORK INITIALIZATION CLEANUP: Removing stale temporary data")
        
        try:
            # Clean framework-level temporary data
            temp_repos_path = self.framework_root / 'temp_repos'
            
            cleanup_stats = {
                'files_removed': 0,
                'directories_removed': 0,
                'bytes_cleaned': 0
            }
            
            if temp_repos_path.exists():
                logger.info(f"🗑️ Removing stale temp_repos directory: {temp_repos_path}")
                
                # Calculate size before removal
                size_cleaned = self._calculate_directory_size(temp_repos_path)
                
                # Remove the directory
                import shutil
                shutil.rmtree(temp_repos_path, ignore_errors=True)
                
                cleanup_stats['directories_removed'] = 1
                cleanup_stats['bytes_cleaned'] = size_cleaned
                
                logger.info(f"✅ Removed stale temp_repos ({self._format_bytes(size_cleaned)})")
            
            # Clean any other framework-level temp directories
            for temp_dir in ['.tmp', 'cache', 'staging']:
                temp_path = self.framework_root / temp_dir
                if temp_path.exists() and temp_path.is_dir():
                    logger.info(f"🗑️ Removing framework temp directory: {temp_path}")
                    size_cleaned = self._calculate_directory_size(temp_path)
                    import shutil
                    shutil.rmtree(temp_path, ignore_errors=True)
                    cleanup_stats['directories_removed'] += 1
                    cleanup_stats['bytes_cleaned'] += size_cleaned
            
            summary = f"Cleaned {cleanup_stats['directories_removed']} directories, {self._format_bytes(cleanup_stats['bytes_cleaned'])}"
            
            result = {
                'success': True,
                'cleanup_statistics': cleanup_stats,
                'summary': summary,
                'hook_type': 'framework_initialization'
            }
            
            if cleanup_stats['directories_removed'] > 0:
                logger.info(f"✅ Framework initialization cleanup: {summary}")
            else:
                logger.info("✅ Framework initialization cleanup: No stale data found")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Framework initialization cleanup failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'cleanup_statistics': {'files_removed': 0, 'directories_removed': 0, 'bytes_cleaned': 0}
            }
    
    def manual_cleanup_hook(self, target_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Hook: Manual cleanup triggered by user or CI/CD
        
        Args:
            target_path: Optional specific path to clean (defaults to current directory)
            
        Returns:
            Dict with cleanup results
        """
        if target_path is None:
            target_path = str(self.framework_root)
        
        logger.info(f"🧹 MANUAL CLEANUP HOOK: Cleaning {target_path}")
        
        try:
            result = self.cleanup_service.execute_comprehensive_cleanup(target_path)
            
            if result['success']:
                logger.info(f"✅ Manual cleanup completed: {result['summary']}")
            else:
                logger.warning(f"⚠️ Manual cleanup had issues: {result.get('error', 'Unknown')}")
            
            result['hook_type'] = 'manual'
            return result
            
        except Exception as e:
            logger.error(f"❌ Manual cleanup hook failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'cleanup_statistics': {'files_removed': 0, 'directories_removed': 0, 'bytes_cleaned': 0},
                'hook_type': 'manual'
            }
    
    def emergency_cleanup_hook(self) -> Dict[str, Any]:
        """
        Hook: Emergency cleanup to free space when system is running low
        
        This performs aggressive cleanup of all temporary data across the framework.
        
        Returns:
            Dict with cleanup results
        """
        logger.warning("🚨 EMERGENCY CLEANUP HOOK: Performing aggressive cleanup")
        
        try:
            total_stats = {
                'files_removed': 0,
                'directories_removed': 0,
                'bytes_cleaned': 0
            }
            
            # 1. Clean framework root
            framework_result = self.framework_initialization_cleanup_hook()
            if framework_result['success']:
                stats = framework_result['cleanup_statistics']
                total_stats['directories_removed'] += stats['directories_removed']
                total_stats['bytes_cleaned'] += stats['bytes_cleaned']
            
            # 2. Clean entire runs directory
            runs_path = self.framework_root / 'runs'
            if runs_path.exists():
                runs_result = self.cleanup_service.execute_comprehensive_cleanup(str(runs_path))
                if runs_result['success']:
                    stats = runs_result['cleanup_statistics']
                    total_stats['files_removed'] += stats['files_removed']
                    total_stats['directories_removed'] += stats['directories_removed']
                    total_stats['bytes_cleaned'] += stats['bytes_cleaned']
            
            summary = f"Emergency cleanup: {total_stats['files_removed']} files, {total_stats['directories_removed']} directories, {self._format_bytes(total_stats['bytes_cleaned'])} freed"
            
            logger.warning(f"🚨 Emergency cleanup completed: {summary}")
            
            return {
                'success': True,
                'cleanup_statistics': total_stats,
                'summary': summary,
                'hook_type': 'emergency'
            }
            
        except Exception as e:
            logger.error(f"❌ Emergency cleanup hook failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'cleanup_statistics': {'files_removed': 0, 'directories_removed': 0, 'bytes_cleaned': 0},
                'hook_type': 'emergency'
            }
    
    def _calculate_directory_size(self, path: Path) -> int:
        """Calculate total size of directory in bytes"""
        total_size = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    total_size += item.stat().st_size
        except (OSError, PermissionError):
            pass
        return total_size
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"

# Global hook instance
cleanup_hook = ComprehensiveCleanupHook()

# Convenience functions for easy integration

def post_execution_cleanup(run_directory: str) -> Dict[str, Any]:
    """Convenience function for post-execution cleanup"""
    return cleanup_hook.post_execution_cleanup_hook(run_directory)

def framework_initialization_cleanup() -> Dict[str, Any]:
    """Convenience function for framework initialization cleanup"""
    return cleanup_hook.framework_initialization_cleanup_hook()

def manual_cleanup(target_path: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function for manual cleanup"""
    return cleanup_hook.manual_cleanup_hook(target_path)

def emergency_cleanup() -> Dict[str, Any]:
    """Convenience function for emergency cleanup"""
    return cleanup_hook.emergency_cleanup_hook()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive Cleanup Hook System")
    parser.add_argument("--hook-type", choices=['post-execution', 'initialization', 'manual', 'emergency'],
                       default='manual', help="Type of cleanup hook to execute")
    parser.add_argument("--target", type=str, help="Target directory for cleanup (manual mode only)")
    parser.add_argument("--verbose", action='store_true', help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    print("🧹 COMPREHENSIVE CLEANUP HOOK SYSTEM")
    print("=" * 50)
    print(f"Hook Type: {args.hook_type}")
    if args.target:
        print(f"Target: {args.target}")
    print()
    
    try:
        if args.hook_type == 'post-execution':
            if not args.target:
                print("❌ Error: --target required for post-execution cleanup")
                sys.exit(1)
            result = post_execution_cleanup(args.target)
        elif args.hook_type == 'initialization':
            result = framework_initialization_cleanup()
        elif args.hook_type == 'manual':
            result = manual_cleanup(args.target)
        elif args.hook_type == 'emergency':
            result = emergency_cleanup()
        
        print(f"Status: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
        print(f"Summary: {result.get('summary', 'No summary available')}")
        
        if 'cleanup_statistics' in result:
            stats = result['cleanup_statistics']
            print(f"Files Removed: {stats['files_removed']}")
            print(f"Directories Removed: {stats['directories_removed']}")
            print(f"Bytes Cleaned: {cleanup_hook._format_bytes(stats['bytes_cleaned'])}")
        
        if 'error' in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Hook execution failed: {e}")
        sys.exit(1)