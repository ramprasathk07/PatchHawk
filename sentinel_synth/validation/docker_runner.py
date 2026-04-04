import os
import tempfile
import subprocess
import shutil

# To support --no-docker or environments where docker isn't running yet.
def run_code(code: str, timeout_sec: int = 5, use_docker: bool = True) -> dict:
    """
    Executes Python code in an isolated environment.
    If use_docker is True, runs in `sentinel-sandbox:latest`.
    If False, runs locally using subprocess (UNSAFE for real workloads, but fine for demo/dev).
    """
    temp_dir = tempfile.mkdtemp(prefix="sentinel_sandbox_")
    script_path = os.path.join(temp_dir, "script.py")
    
    with open(script_path, "w") as f:
        f.write(code)
        
    result = {
        "stdout": "",
        "stderr": "",
        "exit_code": -1,
        "network_blocked": use_docker,
        "file_writes": []
    }

    try:
        if use_docker:
            # We assume docker CLI is available. 
            # `docker run --rm --network none --memory 256m --cpus 0.5 -v temp_dir:/app sentinel-sandbox python /app/script.py`
            cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", "256m",
                "--cpus", "0.5",
                "-v", f"{temp_dir}:/app",
                "sentinel-sandbox:latest",
                "python", "/app/script.py"
            ]
        else:
            # Local fallback (UNSAFE but necessary if Docker is unavailable)
            cmd = ["python3", script_path]
            
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec
        )
        
        result["stdout"] = process.stdout
        result["stderr"] = process.stderr
        result["exit_code"] = process.returncode
        
        # Check if the code wrote any *new* files to the temp dir
        for filename in os.listdir(temp_dir):
            if filename != "script.py":
                result["file_writes"].append(filename)
                
    except subprocess.TimeoutExpired as e:
        result["stderr"] = "Execution timed out."
        if use_docker and hasattr(e, 'stdout') and e.stdout:
             result["stdout"] = e.stdout.decode('utf-8', errors='ignore') if isinstance(e.stdout, bytes) else e.stdout
            
    except Exception as e:
        result["stderr"] = f"Execution error: {str(e)}"
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    return result

def check_syntax(code: str, use_docker: bool = True) -> tuple[bool, str]:
    """Check python syntax of the code without fully executing it."""
    temp_dir = tempfile.mkdtemp(prefix="sentinel_syntax_")
    script_path = os.path.join(temp_dir, "script.py")
    
    with open(script_path, "w") as f:
        f.write(code)
        
    try:
        if use_docker:
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{temp_dir}:/app",
                "sentinel-sandbox:latest",
                "python", "-m", "py_compile", "/app/script.py"
            ]
        else:
            cmd = ["python3", "-m", "py_compile", script_path]
            
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        if process.returncode == 0:
            return True, ""
        else:
            return False, process.stderr
    except subprocess.TimeoutExpired:
         return False, "Syntax check timed out"
    except Exception as e:
         return False, f"Syntax check failed: {e}"
    finally:
         shutil.rmtree(temp_dir, ignore_errors=True)
