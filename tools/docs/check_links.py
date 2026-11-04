"""Checks that relative links in the repository's Markdown files point to existing files.

Usage: python tools/docs/check_links.py [root]. Exits with status 1 if a link is broken.
External links (http, https, mailto) and in-page anchors are not checked.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKIPPED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "target",
    "build",
    "dist",
    ".dart_tool",
    ".pytest_cache",
    ".ruff_cache",
}
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")


def markdown_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if not SKIPPED_DIRS.intersection(part for part in path.relative_to(root).parts)
    )


def broken_links(path: Path, root: Path) -> list[str]:
    problems = []
    in_fence = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in LINK.findall(INLINE_CODE.sub("", line)):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            relative = target.split("#", 1)[0]
            resolved = (path.parent / relative).resolve()
            if not resolved.exists():
                problems.append(f"{path.relative_to(root)}:{number}: lien cassé vers {target}")
    return problems


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    files = markdown_files(root)
    problems = [problem for path in files for problem in broken_links(path, root)]
    for problem in problems:
        print(problem)
    print(f"{len(files)} fichiers Markdown vérifiés, {len(problems)} lien(s) cassé(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
