#!/usr/bin/env python3
"""
Validate that no tools or episodes have piping in args arrays
"""
import json
import glob
import sys

errors = []

# Check all tool files
for tool_file in glob.glob("data/permanent_tools/**/tool_*.json", recursive=True):
    with open(tool_file) as f:
        try:
            data = json.load(f)
            for seq in data.get("sequence", []):
                args = seq.get("action", {}).get("args", [])
                if isinstance(args, list) and "|" in args:
                    errors.append(f"{tool_file}: Found pipe '|' in args array")
        except json.JSONDecodeError:
            errors.append(f"{tool_file}: Invalid JSON")

# Check all episode files
for ep_file in glob.glob("data/episodes/**/episode_*.json", recursive=True):
    with open(ep_file) as f:
        try:
            data = json.load(f)
            for step in data.get("steps", []):
                args = step.get("action", {}).get("args", [])
                if isinstance(args, list) and "|" in args:
                    errors.append(f"{ep_file}: Found pipe '|' in args array")
        except json.JSONDecodeError:
            errors.append(f"{ep_file}: Invalid JSON")

if errors:
    print("VALIDATION ERRORS:")
    for err in errors:
        print(f"  - {err}")
    sys.exit(1)
else:
    print("✓ All files validated - no piping in args arrays")
    sys.exit(0)
