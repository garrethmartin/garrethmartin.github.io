#!/usr/bin/env python3
"""Regenerate auto-generated pages and optionally serve the site locally.

Usage:
    python update_website.py           # update publications + repos pages
    python update_website.py --serve   # also launch jekyll serve afterward
"""

import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))


def run(label, script, *args):
    print(f"\n=== {label} ===")
    cmd = [sys.executable, os.path.join(ROOT, script), *args]
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"ERROR: {script} failed (exit {result.returncode})")
        sys.exit(result.returncode)


def main():
    run("Generating publications page", "generate_publist.py")
    run("Generating repositories page", "generate_repos.py")
    run("Fetching citation statistics", "fetch_stats.py", "--update-pages")
    print("\nDone. All pages updated.")

    if "--serve" in sys.argv:
        print("\n=== Starting Jekyll server ===")
        subprocess.run(["bundle", "exec", "jekyll", "serve"], cwd=ROOT)


if __name__ == "__main__":
    main()
