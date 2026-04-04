import os
import tempfile
import textwrap
from .docker_runner import run_code, check_syntax

def validate_patch(scenario: dict, patch_code: str, use_docker: bool = True) -> tuple[bool, str, dict]:
    """
    Validates a patch using a 3-step pipeline:
    1. Syntax Check
    2. Unit Test Execution
    3. Re-attack (Vulnerability Verification)
    
    Returns: (success, message, details_dict)
    """
    details = {}
    
    # 1. Syntax Check
    is_valid, err_msg = check_syntax(patch_code, use_docker=use_docker)
    if not is_valid:
        details["error"] = err_msg
        return False, "Syntax error", details
        
    # 2. Unit Test Execution
    if scenario.get("unit_test_code"):
        # We need to run the unit test code.
        # test.py contains something like: "import code; assert code.func() == expected"
        # We write patched code to a module 'code.py', and run 'test.py'
        
        # We can construct a combined script that writes the 'code' module dynamically,
        # or we just embed the patched code and the test code in one unified runner.
        # Easiest way in a single file runner (since docker_runner runs a single script):
        combined_script = f"""import sys
import types

# Create a mock 'code' module
module = types.ModuleType('code')
exec('''{patch_code}''', module.__dict__)
sys.modules['code'] = module

# Run the unit test
{scenario['unit_test_code']}
print("TEST_SUCCESS")
"""
        
        result = run_code(combined_script, timeout_sec=5, use_docker=use_docker)
        if result["exit_code"] != 0 or "TEST_SUCCESS" not in result["stdout"]:
            details["test_output"] = result["stderr"] if result["stderr"] else result["stdout"]
            return False, "Unit test failed", details
            
    # 3. Re-attack (Vulnerability Verification)
    if scenario["type"] == "true_positive" and scenario.get("attack_type"):
        # Run original code snippet to get baseline malicious behavior
        attack_result = run_code(scenario["code_snippet"], timeout_sec=5, use_docker=use_docker)
        
        # Run patched code
        patch_result = run_code(patch_code, timeout_sec=5, use_docker=use_docker)
        
        vulnerability_remains = False
        
        # Generic heuristic: Did the patch reduce suspicious side-effects?
        # 1. Compare file writes (malicious often creates/modifies files)
        if len(patch_result.get("file_writes", [])) >= len(attack_result.get("file_writes", [])) and len(attack_result.get("file_writes", [])) > 0:
             # Basic check: if attack result has file writes and patch still has them or more
             vulnerability_remains = True
             
        # 2. Compare network attempts (if telemetry includes it)
        if patch_result.get("network_blocked") and attack_result.get("network_blocked"):
             vulnerability_remains = True
             
        # 3. Specific attack type checks (refined)
        if scenario["attack_type"] == "typosquatting":
            if "ImportError" in patch_result["stderr"] and "pythonn" in patch_result["stderr"]:
                vulnerability_remains = True
        elif scenario["attack_type"] == "obfuscated_exec":
            # If the patch still produces the same specific output as the obfuscated one
            if attack_result["stdout"].strip() != "" and patch_result["stdout"] == attack_result["stdout"]:
                 vulnerability_remains = True

        if vulnerability_remains:
            details["evidence"] = {
                "attack_telemetry": attack_result,
                "patch_telemetry": patch_result
            }
            return False, "Vulnerability still accessible", details

    details["validation_log"] = "All checks passed successfully."
    return True, "Patch is valid", details
