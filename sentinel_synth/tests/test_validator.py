import pytest
from sentinel_synth.validation.patch_validator import validate_patch

def test_syntax_error_detected():
    scenario = {"type": "functional", "code_snippet": "print('hello')", "unit_test_code": None}
    patch = "print('hello"  # Missing closing quote
    
    success, msg, details = validate_patch(scenario, patch, use_docker=False)
    
    assert success is False
    assert msg == "Syntax error"
    assert "error" in details

def test_unit_test_pass():
    scenario = {
        "type": "functional", 
        "code_snippet": "def add(a, b): return a + b",
        "unit_test_code": "import code\nassert code.add(1, 2) == 3\n"
    }
    patch = "def add(a, b):\n    return a + b\n"
    
    success, msg, details = validate_patch(scenario, patch, use_docker=False)
    
    assert success is True
    assert msg == "Patch is valid"

def test_unit_test_fail():
    scenario = {
        "type": "functional", 
        "code_snippet": "def add(a, b): return a + b",
        "unit_test_code": "import code\nassert code.add(1, 2) == 3\n"
    }
    # Breaking the functionality in the patch
    patch = "def add(a, b):\n    return a - b\n"
    
    success, msg, details = validate_patch(scenario, patch, use_docker=False)
    
    assert success is False
    assert msg == "Unit test failed"
    assert "test_output" in details

def test_vulnerability_remains():
    # Attack injects a hidden print which simulates a backdoor 
    scenario = {
        "type": "true_positive",
        "attack_type": "obfuscated_exec",
        "code_snippet": "print('Hello from hidden exec!')\ndef add(a, b): return a + b",
        "unit_test_code": "import code\nassert code.add(1, 2) == 3\n"
    }
    # Patch fails to remove the backdoor, only formats the code
    patch = "print('Hello from hidden exec!')\ndef add(a, b):\n    return a + b\n"
    
    success, msg, details = validate_patch(scenario, patch, use_docker=False)
    
    assert success is False
    assert msg == "Vulnerability remains"
    assert "evidence" in details
