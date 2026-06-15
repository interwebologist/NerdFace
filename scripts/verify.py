import subprocess
import json
import sys
import os
import shlex

# Descriptions of verification tools
TOOL_DESCRIPTIONS = {
    "Linter (Ruff)": "Fast Python linter (PEP 8, common bugs, import sorting).",
    "Formatter (Ruff)": "Checks code style and consistent indentation.",
    "Type Check (Mypy)": "Static type checker to find logic errors and type mismatches.",
    "Security (Bandit)": "Security linter to find vulnerabilities (hardcoded keys, unsafe exec).",
    "Dead Code (Vulture)": "Finds unused functions, classes, and global variables.",
    "JSON Syntax Check": "Ensures all JSON configuration files are syntactically valid.",
    "Tests (Pytest)": "Runs automated test suite to verify behavioral correctness.",
}


def run_check(name, cmd):
    """Runs a command and returns a structured result."""
    desc = TOOL_DESCRIPTIONS.get(name, "")
    print(f"Running {name}... ({desc})")
    proc = subprocess.run(
        shlex.split(cmd), capture_output=True, text=True, shell=False
    )
    # Special case for pytest: "no tests ran" is not a failure
    if name == "Tests (Pytest)" and "no tests ran" in proc.stdout:
        return {
            "tool": name,
            "success": True,
            "output": "Passed (no tests found)",
            "error": proc.stderr,
        }
    return {
        "tool": name,
        "success": proc.returncode == 0,
        "output": proc.stdout if proc.returncode != 0 else "Passed",
        "error": proc.stderr,
    }


def check_json_files():
    """Check all JSON files for valid syntax."""
    name = "JSON Syntax Check"
    desc = TOOL_DESCRIPTIONS.get(name, "")
    print(f"Checking {name}... ({desc})")
    json_files = []
    for root, dirs, files in os.walk("."):
        # Skip hidden directories and common build/cache directories
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".")
            and d not in ["__pycache__", "node_modules", "dist", "build"]
        ]
        for file in files:
            if file.endswith(".json"):
                json_files.append(os.path.join(root, file))

    errors = []
    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"{json_file}: {str(e)}")
        except Exception as e:
            errors.append(f"{json_file}: {str(e)}")

    if errors:
        return {
            "tool": name,
            "success": False,
            "output": "\n".join(errors),
            "error": "",
        }
    else:
        return {
            "tool": name,
            "success": True,
            "output": f"Passed ({len(json_files)} files checked)",
            "error": "",
        }


def main():
    # 1. Static Analysis & Linting
    checks = [
        run_check("Linter (Ruff)", "uv run ruff check --output-format json ."),
        run_check("Formatter (Ruff)", "uv run ruff format --check ."),
        run_check("Type Check (Mypy)", "uv run mypy . --ignore-missing-imports"),
        run_check("Security (Bandit)", "uv run bandit -r . -x ./tests,./.venv -ll"),
        run_check("Dead Code (Vulture)", "uv run vulture . --exclude .venv,tests"),
        check_json_files(),
    ]

    # 2. Pytest Execution
    checks.append(
        run_check(
            "Tests (Pytest)",
            "uv run pytest --json-report --json-report-file=.report.json --quiet",
        )
    )

    # Summary Generation
    failed = [c for c in checks if not c["success"]]

    if not failed:
        print("\n✅ ALL CHECKS PASSED. READY FOR PR.")
        sys.exit(0)
    else:
        print("\n❌ CHECKS FAILED. See summary below:")
        for f in failed:
            print(f"\n--- {f['tool']} Failure ---")
            print(f["output"])
            if f["error"]:
                print(f"Error output: {f['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
