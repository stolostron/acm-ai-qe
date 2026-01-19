#!/usr/bin/env python3
"""
Execution Verification Hook - Prevents fictional execution claims
Automatically validates any execution claims with required evidence
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ExecutionVerificationHook:
    """Hook to verify execution claims and prevent fictional data"""
    
    def __init__(self):
        self.execution_keywords = [
            'fresh execution', 'executed', 'ran the', 'running', 
            'execution completed', 'command output', 'framework run'
        ]
        self.required_evidence = [
            'pwd', 'ls -la', 'timestamp', 'bash', 'python'
        ]
    
    def validate_execution_claim(self, response_text: str) -> Dict[str, Any]:
        """
        Validate any execution claims in the response
        
        Args:
            response_text: The response text to validate
            
        Returns:
            Validation results with pass/fail and evidence analysis
        """
        validation_result = {
            'has_execution_claims': False,
            'has_required_evidence': False,
            'missing_evidence': [],
            'validation_passed': True,
            'warnings': [],
            'errors': []
        }
        
        # Check for execution claims
        execution_claims = []
        for keyword in self.execution_keywords:
            if keyword.lower() in response_text.lower():
                execution_claims.append(keyword)
                validation_result['has_execution_claims'] = True
        
        if not validation_result['has_execution_claims']:
            return validation_result
        
        # If execution claims found, verify evidence
        evidence_found = []
        missing_evidence = []
        
        for evidence in self.required_evidence:
            if evidence in response_text.lower():
                evidence_found.append(evidence)
            else:
                missing_evidence.append(evidence)
        
        validation_result['missing_evidence'] = missing_evidence
        validation_result['has_required_evidence'] = len(evidence_found) >= 3
        
        # Validate execution patterns
        if validation_result['has_execution_claims']:
            if not validation_result['has_required_evidence']:
                validation_result['validation_passed'] = False
                validation_result['errors'].append(
                    f"EXECUTION CLAIM WITHOUT EVIDENCE: Found claims {execution_claims} "
                    f"but missing required evidence: {missing_evidence}"
                )
            
            # Check for forbidden patterns
            forbidden_patterns = [
                'fictional', 'constructed', 'created.*output', 
                'generated.*data', 'simulated.*execution'
            ]
            
            for pattern in forbidden_patterns:
                if re.search(pattern, response_text, re.IGNORECASE):
                    validation_result['validation_passed'] = False
                    validation_result['errors'].append(
                        f"FORBIDDEN PATTERN DETECTED: {pattern} - indicates fictional execution"
                    )
        
        return validation_result
    
    def enforce_evidence_requirements(self, response_text: str) -> str:
        """
        Enforce evidence requirements by modifying response if needed
        
        Args:
            response_text: Original response text
            
        Returns:
            Modified response with evidence enforcement
        """
        validation = self.validate_execution_claim(response_text)
        
        if not validation['validation_passed']:
            enforcement_notice = """
🚨 EXECUTION EVIDENCE VIOLATION DETECTED

This response contains execution claims without required evidence:

ERRORS:
""" + "\n".join(f"- {error}" for error in validation['errors']) + """

REQUIRED EVIDENCE PATTERN:
```bash
# Show working directory
pwd

# Show file timestamps BEFORE execution
ls -la runs/*/latest/

# Show actual command execution with output
[actual command]

# Show file timestamps AFTER execution  
ls -la [new files]
```

RESPONSE BLOCKED: Please provide actual execution evidence or clarify this is analysis of existing files.
"""
            return enforcement_notice
        
        return response_text

def create_execution_verification_hook():
    """Factory function to create the hook"""
    return ExecutionVerificationHook()

# Hook registration for Claude Code
HOOK_CONFIG = {
    "name": "execution_verification",
    "description": "Prevents fictional execution claims",
    "trigger_patterns": ["execution", "fresh", "ran", "executed"],
    "enforcement_level": "strict",
    "auto_validate": True
}

# Claude Code hook interface - REQUIRED FUNCTION
def claude_code_tool_hook(tool_name: str, args: Dict[str, Any], result: Any, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Claude Code hook interface for execution verification
    
    This hook validates execution claims to prevent fictional data generation.
    It ensures that any claims of running/executing commands have proper evidence.
    
    Args:
        tool_name: Name of the tool being executed
        args: Tool arguments
        result: Tool execution result
        **kwargs: Additional context
        
    Returns:
        Hook metadata with validation results
    """
    
    # Initialize the verification hook
    hook = create_execution_verification_hook()
    
    # Tools that might make execution claims
    verification_tools = ['Bash', 'Write', 'Edit', 'MultiEdit']
    
    # Only verify for relevant tools
    if tool_name not in verification_tools:
        return None
    
    # Extract response text to validate
    response_text = ""
    if isinstance(result, str):
        response_text = result
    elif isinstance(result, dict):
        response_text = str(result.get('output', '')) + str(result.get('content', ''))
    
    # Validate execution claims
    validation = hook.validate_execution_claim(response_text)
    
    # Log validation results
    if not validation['validation_passed']:
        logger.warning(f"Execution verification failed for {tool_name}: {validation['errors']}")
        
        # Return validation failure metadata
        return {
            'hook_name': 'execution_verification',
            'validation_failed': True,
            'errors': validation['errors'],
            'missing_evidence': validation['missing_evidence'],
            'enforcement_message': hook.enforce_evidence_requirements(response_text)
        }
    
    # Return success metadata
    return {
        'hook_name': 'execution_verification',
        'validation_passed': True,
        'tool_name': tool_name,
        'has_execution_claims': validation['has_execution_claims'],
        'has_required_evidence': validation['has_required_evidence']
    }

if __name__ == "__main__":
    # Test the hook
    hook = create_execution_verification_hook()
    
    # Test case 1: Execution claim without evidence
    test_response = "I ran a fresh execution of the framework and got these results..."
    result = hook.validate_execution_claim(test_response)
    print(f"Test 1 - Validation passed: {result['validation_passed']}")
    
    # Test case 2: Execution claim with evidence
    test_response_good = """
    I executed the framework with these commands:
    
    pwd
    /Users/test/framework
    
    ls -la runs/*/latest/
    -rw-r--r-- 1 user staff 1234 Aug 27 15:30 output.json
    
    python3 run_framework.py
    Framework execution completed successfully
    
    ls -la runs/ACM-22079/
    -rw-r--r-- 1 user staff 5678 Aug 27 15:45 new_results.json
    """
    result2 = hook.validate_execution_claim(test_response_good)
    print(f"Test 2 - Validation passed: {result2['validation_passed']}")