"""
PatchHawk sandbox — Docker-based isolated code execution and
three-stage patch validation pipeline.

Execution constraints (Docker mode):
    --network none   (no outbound connections)
    --memory 256m    (hard memory cap)
    --cpus 0.5       (half a CPU core)

Falls back to local subprocess when use_docker=False (dev/CI only).
"""

import os
import shutil
import subprocess
import tempfile
from typing import Dict, Any


# =====================================================================
# Code Execution
# =====================================================================


def run_code(
    code: str,
    timeout_sec: int = 5,
    use_docker: bool = True,
) -> Dict[str, Any]:
    """Execute *code* in an isolated sandbox and return telemetry."""
    temp_dir = tempfile.mkdtemp(prefix="patchhawk_sandbox_")
    script_path = os.path.join(temp_dir, "script.py")

    with open(script_path, "w") as f:
        f.write(code)

    result: Dict[str, Any] = {
        "stdout": "",
        "stderr": "",
        "exit_code": -1,
        "network_blocked": use_docker,
        "file_writes": [],
    }

    try:
        if use_docker:
            cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", "256m",
                "--cpus", "0.5",
                "-v", f"{temp_dir}:/app:rw",
                "patchhawk-sandbox:latest",
                "python", "/app/script.py",
            ]
        else:
            cmd = ["python3", script_path]

        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_sec
        )
        result["stdout"] = proc.stdout
        result["stderr"] = proc.stderr
        result["exit_code"] = proc.returncode

        # Record any new files the code wrote
        for fname in os.listdir(temp_dir):
            if fname != "script.py":
                result["file_writes"].append(fname)

    except subprocess.TimeoutExpired:
        result["stderr"] = "Execution timed out."
    except Exception as exc:
        result["stderr"] = f"Execution error: {exc}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return result


def check_syntax(
    code: str,
    use_docker: bool = True,
) -> tuple:
    """Run ``python -m py_compile`` and return (ok: bool, error_msg: str)."""
    temp_dir = tempfile.mkdtemp(prefix="patchhawk_syntax_")
    script_path = os.path.join(temp_dir, "script.py")

    with open(script_path, "w") as f:
        f.write(code)

    try:
        if use_docker:
            cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", "256m",
                "--cpus", "0.5",
                "-v", f"{temp_dir}:/app:ro",
                "patchhawk-sandbox:latest",
                "python", "-m", "py_compile", "/app/script.py",
            ]
        else:
            cmd = ["python3", "-m", "py_compile", script_path]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            return True, ""
        return False, proc.stderr

    except subprocess.TimeoutExpired:
        return False, "Syntax check timed out"
    except Exception as exc:
        return False, f"Syntax check failed: {exc}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# =====================================================================
# Three-Stage Patch Validation
# =====================================================================


def validate_patch(
    scenario: dict,
    patch_code: str,
    use_docker: bool = True,
) -> tuple:
    """
    Returns (success: bool, message: str, details: dict).

    Stages:
        1. Syntax check — python -m py_compile on patched code
        2. Unit test execution — run unit_test_code against patched code
        3. Re-attack — compare malicious vs patched side-effects
    """
    details: dict = {}

    # ------------------------------------------------------------------
    # Stage 1 – Syntax
    # ------------------------------------------------------------------
    ok, err = check_syntax(patch_code, use_docker=use_docker)
    if not ok:
        details["error"] = err
        return False, "Syntax error", details

    # ------------------------------------------------------------------
    # Stage 2 – Unit test
    # ------------------------------------------------------------------
    test_code = scenario.get("unit_test_code")
    if test_code:
        combined = (
            "import sys, types\n"
            "mod = types.ModuleType('code')\n"
            f"exec('''{patch_code}''', mod.__dict__)\n"
            "sys.modules['code'] = mod\n"
            f"{test_code}\n"
            "print('TEST_SUCCESS')\n"
        )
        res = run_code(combined, timeout_sec=5, use_docker=use_docker)
        if res["exit_code"] != 0 or "TEST_SUCCESS" not in res["stdout"]:
            details["test_output"] = res["stderr"] or res["stdout"]
            return False, "Unit test failed", details

    # ------------------------------------------------------------------
    # Stage 3 – Re-attack verification
    # ------------------------------------------------------------------
    if scenario.get("type") == "true_positive" and scenario.get("attack_type"):
        attack_res = run_code(scenario["code_snippet"], timeout_sec=5, use_docker=use_docker)
        patch_res = run_code(patch_code, timeout_sec=5, use_docker=use_docker)

        vulnerability_remains = False

        # Check file-write side-effects
        if (
            len(attack_res.get("file_writes", [])) > 0
            and len(patch_res.get("file_writes", []))
            >= len(attack_res.get("file_writes", []))
        ):
            vulnerability_remains = True

        # Attack-type-specific heuristics
        attack_type = scenario["attack_type"]
        if attack_type == "typosquatting":
            if "pythonn" in patch_res.get("stderr", ""):
                vulnerability_remains = True
        elif attack_type == "obfuscated_exec":
            if (
                attack_res["stdout"].strip()
                and patch_res["stdout"] == attack_res["stdout"]
            ):
                vulnerability_remains = True
        elif attack_type == "subprocess_backdoor":
            if "nc" in patch_code or "subprocess.call" in patch_code:
                vulnerability_remains = True
        elif attack_type == "socket_exfil":
            if "socket" in patch_code and "connect" in patch_code:
                vulnerability_remains = True
        elif attack_type == "env_hijack":
            if "os.environ" in patch_code and "PATH" in patch_code:
                vulnerability_remains = True

        if vulnerability_remains:
            details["evidence"] = {
                "attack_telemetry": attack_res,
                "patch_telemetry": patch_res,
            }
            return False, "Vulnerability still accessible", details

    details["validation_log"] = "All checks passed successfully."
    return True, "Patch is valid", details
