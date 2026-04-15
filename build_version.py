#!/usr/bin/env python3
"""
Auto-increment version based on git tags.
Generates next patch version (e.g., v1.0.0 -> v1.0.1)
"""

import subprocess
import sys
from packaging import version


def get_latest_tag():
    """Get the latest git tag that matches v*.*.* pattern"""
    try:
        # Get all tags sorted by version
        result = subprocess.run(
            ["git", "tag", "-l", "v*.*.*", "--sort=-version:refname"],
            capture_output=True,
            text=True,
            check=True
        )
        tags = result.stdout.strip().split("\n")
        if tags and tags[0]:
            return tags[0]
    except subprocess.CalledProcessError:
        pass
    return None


def increment_patch_version(tag):
    """Increment patch version (v1.0.0 -> v1.0.1)"""
    try:
        ver = version.parse(tag.lstrip("v"))
        major, minor, patch = ver.major, ver.minor, ver.micro
        new_version = f"v{major}.{minor}.{patch + 1}"
        return new_version
    except Exception as e:
        print(f"Error parsing version: {e}", file=sys.stderr)
        return "v1.0.0"


def main():
    latest_tag = get_latest_tag()
    
    if latest_tag:
        new_version = increment_patch_version(latest_tag)
        print(f"Latest tag: {latest_tag}")
        print(f"New version: {new_version}")
    else:
        new_version = "v1.0.0"
        print("No tags found. Starting with v1.0.0")
    
    # Output for GitHub Actions
    print(f"VERSION={new_version.lstrip('v')}")
    with open("version.txt", "w") as f:
        f.write(new_version.lstrip("v"))
    
    return new_version


if __name__ == "__main__":
    main()
