#!/usr/bin/env python3
"""Utility script to rename the project and source package."""

import keyword
import re
import shutil
import subprocess
import sys
from pathlib import Path


def to_valid_identifier(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"pkg_{cleaned}"
    cleaned = cleaned.lower()
    if keyword.iskeyword(cleaned):
        cleaned = f"pkg_{cleaned}"
    return cleaned


def rename_project(raw_name: str) -> None:
    root_dir = Path(__file__).resolve().parent.parent
    dist_name = raw_name.strip()
    if not dist_name:
        print("Error: Project name cannot be empty.", file=sys.stderr)
        sys.exit(1)

    if not re.match(r"^[a-zA-Z0-9_-]+$", dist_name):
        print(
            "Error: Project name can only contain letters, numbers, "
            "hyphens, and underscores.",
            file=sys.stderr,
        )
        sys.exit(1)

    module_name = to_valid_identifier(dist_name)

    src_dir = root_dir / "src"
    current_pkgs = sorted(
        [p for p in src_dir.iterdir() if p.is_dir() and (p / "__init__.py").exists()],
        key=lambda p: p.name,
    )
    if not current_pkgs:
        print("Error: Could not find current package in src/", file=sys.stderr)
        sys.exit(1)

    old_pkg_dir = current_pkgs[0]
    old_module_name = old_pkg_dir.name
    new_pkg_dir = src_dir / module_name

    print(f"Renaming module '{old_module_name}' -> '{module_name}'...")
    if old_pkg_dir != new_pkg_dir:
        if new_pkg_dir.exists():
            print(
                f"Error: Target directory '{new_pkg_dir}' already exists.",
                file=sys.stderr,
            )
            sys.exit(1)
        shutil.move(str(old_pkg_dir), str(new_pkg_dir))

    # Update pyproject.toml
    pyproject_file = root_dir / "pyproject.toml"
    if pyproject_file.exists():
        content = pyproject_file.read_text(encoding="utf-8")
        updated = re.sub(
            r'name\s*=\s*"[^"]+"',
            f'name = "{dist_name}"',
            content,
            count=1,
        )
        updated = re.sub(
            r'packages\s*=\s*\[\s*["\']src/[^"\']+["\']\s*\]',
            f'packages = ["src/{module_name}"]',
            updated,
            count=1,
        )
        pyproject_file.write_text(updated, encoding="utf-8")
        print(
            f"Updated pyproject.toml: project name to '{dist_name}', "
            f"packages to 'src/{module_name}'."
        )

    # Update tests/test_smoke.py
    smoke_test = root_dir / "tests" / "test_smoke.py"
    if smoke_test.exists():
        content = smoke_test.read_text(encoding="utf-8")
        content = content.replace(f"import {old_module_name}", f"import {module_name}")
        content = content.replace(f"from {old_module_name}", f"from {module_name}")
        content = content.replace(
            f"{old_module_name}.__version__", f"{module_name}.__version__"
        )
        smoke_test.write_text(content, encoding="utf-8")
        print(f"Updated tests/test_smoke.py to import '{module_name}'.")

    # Sync uv
    print("Re-syncing virtual environment...")
    subprocess.run(["uv", "sync"], cwd=root_dir, check=True)
    print(
        f"\nProject successfully renamed to '{dist_name}' (package: '{module_name}')!"
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/rename.py <new_project_name>")
        sys.exit(1)
    rename_project(sys.argv[1])
