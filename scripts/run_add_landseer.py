#!/usr/bin/env python3
"""
Wrapper to run add_landseer_event.py
"""
import subprocess
import sys
import os

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# Path to the script
script_path = os.path.join(script_dir, 'add_landseer_event.py')

# Path to venv python
venv_python = os.path.join(project_root, 'venv', 'bin', 'python3')

if not os.path.exists(venv_python):
    venv_python = sys.executable

print(f"Running: {script_path}")
print(f"Using Python: {venv_python}")
print("=" * 80)

try:
    result = subprocess.run(
        [venv_python, script_path],
        cwd=project_root,
        capture_output=False,
        text=True
    )
    sys.exit(result.returncode)
except Exception as e:
    print(f"Error running script: {e}")
    sys.exit(1)


