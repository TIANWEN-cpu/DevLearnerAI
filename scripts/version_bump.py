#!/usr/bin/env python3
"""Version bump script for DevLearnerAI.

Reads the current version from pyproject.toml and bumps it.
Syncs the fallback version in app/config.py.

Usage:
    python scripts/version_bump.py patch          # 7.0 -> 7.0.1
    python scripts/version_bump.py minor          # 7.0 -> 7.1.0
    python scripts/version_bump.py major          # 7.0 -> 8.0.0
    python scripts/version_bump.py set 7.2.0      # set exact version
    python scripts/version_bump.py show           # show current version
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_version_from_pyproject() -> str:
    """Read the version string from pyproject.toml."""
    content = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        print("[ERROR] Could not find version in pyproject.toml", file=sys.stderr)
        sys.exit(1)
    return match.group(1)


def parse_version(version: str) -> tuple[int, ...]:
    """Parse a version string into a tuple of ints."""
    parts = version.split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        print(f"[ERROR] Invalid version format: {version}", file=sys.stderr)
        sys.exit(1)


def format_version(parts: tuple[int, ...]) -> str:
    """Format a version tuple back to string."""
    return ".".join(str(p) for p in parts)


def bump_version(current: str, bump_type: str) -> str:
    """Bump version by type (major/minor/patch)."""
    parts = parse_version(current)
    # Ensure we have at least 3 parts
    while len(parts) < 3:
        parts = (*parts, 0)

    major, minor, patch = parts[0], parts[1], parts[2]

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        print(f"[ERROR] Unknown bump type: {bump_type}", file=sys.stderr)
        sys.exit(1)


def update_pyproject_toml(old_version: str, new_version: str) -> None:
    """Update the version in pyproject.toml."""
    path = PROJECT_ROOT / "pyproject.toml"
    content = path.read_text(encoding="utf-8")
    new_content = content.replace(
        f'version = "{old_version}"',
        f'version = "{new_version}"',
        1,
    )
    path.write_text(new_content, encoding="utf-8")
    print(f"  Updated pyproject.toml: {old_version} -> {new_version}")


def update_config_fallback(old_version: str, new_version: str) -> None:
    """Update the fallback version in app/config.py."""
    path = PROJECT_ROOT / "app" / "config.py"
    content = path.read_text(encoding="utf-8")
    # Match the fallback return value: return "X.Y.Z"
    pattern = r'(return\s+)"(\d+\.\d+(?:\.\d+)?)"'
    replacement = rf'\g<1>"{new_version}"'
    new_content, count = re.subn(pattern, replacement, content, count=1)
    if count == 0:
        print("  [WARN] Could not find fallback version in app/config.py")
        return
    path.write_text(new_content, encoding="utf-8")
    print(f"  Updated app/config.py fallback: {old_version} -> {new_version}")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "show":
        current = read_version_from_pyproject()
        print(f"Current version: {current}")
        sys.exit(0)

    if command == "set":
        if len(sys.argv) < 3:
            print("[ERROR] Usage: version_bump.py set <version>", file=sys.stderr)
            sys.exit(1)
        new_version = sys.argv[2]
        # Validate format
        parse_version(new_version)
    elif command in ("major", "minor", "patch"):
        current = read_version_from_pyproject()
        new_version = bump_version(current, command)
    else:
        print(f"[ERROR] Unknown command: {command}", file=sys.stderr)
        print("  Use: major | minor | patch | set <version> | show")
        sys.exit(1)

    current = read_version_from_pyproject()

    if new_version == current:
        print(f"Version is already {current}, nothing to do.")
        sys.exit(0)

    print(f"\nBumping version: {current} -> {new_version}\n")
    update_pyproject_toml(current, new_version)
    update_config_fallback(current, new_version)
    print(f"\nDone. New version: {new_version}")
    print("Remember to commit and tag: git add -A && git commit -m 'bump: v{new_version}' && git tag v{new_version}")


if __name__ == "__main__":
    main()
