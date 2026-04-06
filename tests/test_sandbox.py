"""Tests for the 3-stage patch validation pipeline."""

from patchhawk.agent.sandbox import validate_patch


def test_syntax_error_detected():
    """Stage 1: py_compile catches a missing closing quote."""
    scenario = {
        "type": "functional",
        "code_snippet": "print('hello')",
        "unit_test_code": None,
        "attack_type": None,
    }
    patch = "print('hello"  # syntax error
    success, msg, details = validate_patch(scenario, patch, use_docker=False)
    assert success is False
    assert msg == "Syntax error"
    assert "error" in details


def test_unit_test_pass():
    """Stage 2: a correct patch passes the unit test."""
    scenario = {
        "type": "functional",
        "code_snippet": "def add(a, b): return a + b",
        "unit_test_code": "import code\nassert code.add(1, 2) == 3\n",
        "attack_type": None,
    }
    patch = "def add(a, b):\n    return a + b\n"
    success, msg, details = validate_patch(scenario, patch, use_docker=False)
    assert success is True
    assert msg == "Patch is valid"


def test_unit_test_fail():
    """Stage 2: a broken patch fails the unit test."""
    scenario = {
        "type": "functional",
        "code_snippet": "def add(a, b): return a + b",
        "unit_test_code": "import code\nassert code.add(1, 2) == 3\n",
        "attack_type": None,
    }
    patch = "def add(a, b):\n    return a - b\n"
    success, msg, details = validate_patch(scenario, patch, use_docker=False)
    assert success is False
    assert msg == "Unit test failed"
    assert "test_output" in details


def test_vulnerability_remains():
    """Stage 3: re-attack detects that the backdoor was not removed."""
    scenario = {
        "type": "true_positive",
        "attack_type": "obfuscated_exec",
        "code_snippet": "print('Hello from hidden exec!')\ndef add(a, b): return a + b",
        "unit_test_code": "import code\nassert code.add(1, 2) == 3\n",
    }
    # Patch keeps the backdoor print
    patch = "print('Hello from hidden exec!')\ndef add(a, b):\n    return a + b\n"
    success, msg, details = validate_patch(scenario, patch, use_docker=False)
    assert success is False
    assert msg == "Vulnerability still accessible"
    assert "evidence" in details


def test_clean_patch_passes_reattack():
    """Stage 3: a properly cleaned patch passes re-attack."""
    scenario = {
        "type": "true_positive",
        "attack_type": "obfuscated_exec",
        "code_snippet": "print('Hello from hidden exec!')\ndef add(a, b): return a + b",
        "unit_test_code": "import code\nassert code.add(1, 2) == 3\n",
    }
    # Patch removes the backdoor
    patch = "def add(a, b):\n    return a + b\n"
    success, msg, details = validate_patch(scenario, patch, use_docker=False)
    assert success is True
    assert msg == "Patch is valid"
