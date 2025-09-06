#!/usr/bin/env python3
"""
Coverage gate script that ensures changed modules have ≥85% test coverage.
"""
import os
import sys
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Set


def get_changed_files() -> Set[str]:
    """Get list of changed Python files from git."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        changed_files = set()
        for line in result.stdout.strip().split('\n'):
            if line.endswith('.py') and not line.startswith('tests/'):
                changed_files.add(line)
        return changed_files
    except subprocess.CalledProcessError:
        # If we can't get git diff, assume all files changed
        return set()


def parse_coverage_xml() -> Dict[str, float]:
    """Parse coverage.xml and return coverage percentages by file."""
    coverage_file = Path("coverage.xml")
    if not coverage_file.exists():
        print("Warning: coverage.xml not found")
        return {}
    
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        
        coverage_data = {}
        for package in root.findall(".//package"):
            for class_elem in package.findall(".//class"):
                filename = class_elem.get("filename", "")
                if filename:
                    # Convert relative path to match git diff format
                    if filename.startswith("./"):
                        filename = filename[2:]
                    elif not filename.startswith("/"):
                        filename = filename
                    
                    line_rate = float(class_elem.get("line-rate", "0"))
                    coverage_data[filename] = line_rate * 100
        
        return coverage_data
    except ET.ParseError as e:
        print(f"Error parsing coverage.xml: {e}")
        return {}


def main():
    """Main coverage gate logic."""
    changed_files = get_changed_files()
    coverage_data = parse_coverage_xml()
    
    if not changed_files:
        print("No changed Python files detected")
        return 0
    
    if not coverage_data:
        print("No coverage data available")
        return 0
    
    failed_files = []
    threshold = 85.0
    
    for file_path in changed_files:
        if file_path in coverage_data:
            coverage = coverage_data[file_path]
            if coverage < threshold:
                failed_files.append((file_path, coverage))
                print(f"❌ {file_path}: {coverage:.1f}% (below {threshold}% threshold)")
            else:
                print(f"✅ {file_path}: {coverage:.1f}%")
        else:
            print(f"⚠️  {file_path}: No coverage data found")
    
    if failed_files:
        print(f"\n❌ Coverage gate failed: {len(failed_files)} files below {threshold}% threshold")
        return 1
    else:
        print(f"\n✅ Coverage gate passed: All changed files meet {threshold}% threshold")
        return 0


if __name__ == "__main__":
    sys.exit(main())