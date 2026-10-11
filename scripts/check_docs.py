#!/usr/bin/env python3
"""Check relative Markdown links and the DeepWiki map using only the stdlib."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile("!?\\[[^\\]]+\\]\\(\\s*(?:<([^>]+)>|([^\\s)]+))[^)]*\\)")
HEADING = re.compile("^ {0,3}#{1,6}\\s+(.+?)\\s*#*\\s*$")
HTML_ID = re.compile("<a\\s+(?:[^>]*\\s)?(?:id|name)=[\\\"']([^\\\"']+)[\\\"']", re.IGNORECASE)
INLINE_CODE = re.compile("`+[^`]*`+")


def markdown_files() -> list[Path]:
    files = set(ROOT.glob("*.md"))
    for directory in (ROOT / "docs", ROOT / ".agents"):
        if directory.exists():
            files.update(directory.rglob("*.md"))
    return sorted(files)


def without_code(text: str) -> str:
    output: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        marker = re.match("^\\s{0,3}(```+|~~~+)", line)
        if fence is None and marker:
            fence = marker.group(1)[0]
            continue
        if fence is not None:
            if re.match(f"^\\s{{0,3}}{re.escape(fence)}{{3,}}\\s*$", line):
                fence = None
            continue
        output.append(line)
    return INLINE_CODE.sub("code", "\n".join(output))


def heading_ids(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    found: set[str] = set()
    counts: dict[str, int] = {}
    for line in text.splitlines():
        html = HTML_ID.search(line)
        if html:
            found.add(html.group(1))
        match = HEADING.match(line)
        if not match:
            continue
        title = re.sub("!?(?:\\[([^\\]]+)\\]\\([^)]*\\))", "\\1", match.group(1))
        title = re.sub(r"[`*_~]", "", title)
        slug = re.sub("[^\\w -]", "", title.lower(), flags=re.UNICODE)
        slug = re.sub("\\s+", "-", slug.strip())
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        found.add(slug if count == 0 else f"{slug}-{count}")
    return found


def check_links(files: list[Path]) -> tuple[int, list[str]]:
    checked = 0
    errors: list[str] = []
    anchors_by_file: dict[Path, set[str]] = {}
    for source in files:
        content = without_code(source.read_text(encoding="utf-8"))
        for match in LINK.finditer(content):
            raw = match.group(1) or match.group(2) or ""
            target_url = urlsplit(raw)
            if target_url.scheme or target_url.netloc:
                continue
            checked += 1
            path_text = unquote(target_url.path)
            target = (source.parent / path_text).resolve() if path_text else source
            if target.is_dir():
                if not target_url.fragment:
                    continue
                target = target / "README.md"
            line = content.count("\n", 0, match.start()) + 1
            if not target.is_file():
                errors.append(f"{source.relative_to(ROOT)}:{line}: missing target {raw}")
                continue
            if target_url.fragment:
                anchors = anchors_by_file.setdefault(target, heading_ids(target))
                fragment = unquote(target_url.fragment)
                if fragment not in anchors:
                    errors.append(
                        f"{source.relative_to(ROOT)}:{line}: missing anchor "
                        f"#{fragment} in {target.relative_to(ROOT)}"
                    )
    return checked, errors


def check_wiki() -> list[str]:
    errors: list[str] = []
    wiki = ROOT / "docs" / "wiki"
    for page in sorted(wiki.glob("*.md")):
        lines = len(page.read_text(encoding="utf-8").splitlines())
        if lines > 200:
            errors.append(f"{page.relative_to(ROOT)}: {lines} lines (maximum 200)")

    path = ROOT / ".devin" / "wiki.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f".devin/wiki.json: invalid JSON ({exc})"]

    notes = data.get("repo_notes", [])
    pages = data.get("pages", [])
    if not isinstance(notes, list) or len(notes) > 3:
        errors.append(".devin/wiki.json: repo_notes must contain at most 3 notes")
    else:
        for index, note in enumerate(notes):
            content = note.get("content", "") if isinstance(note, dict) else ""
            if not isinstance(content, str) or len(content) > 10_000:
                errors.append(f".devin/wiki.json: repo_notes[{index}] exceeds 10,000 characters")
    if not isinstance(pages, list) or len(pages) > 30:
        errors.append(".devin/wiki.json: pages must contain at most 30 entries")
        return errors

    titles = [page.get("title") for page in pages if isinstance(page, dict)]
    if len(titles) != len(pages):
        errors.append(".devin/wiki.json: every page must be an object")
    if len(titles) != len(set(titles)):
        errors.append(".devin/wiki.json: page titles must be unique")
    title_set = set(titles)
    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        parent = page.get("parent")
        if parent is not None and parent not in title_set:
            errors.append(f".devin/wiki.json: pages[{index}] has unknown parent {parent!r}")
    return errors


def main() -> int:
    files = markdown_files()
    checked, errors = check_links(files)
    errors.extend(check_wiki())
    for error in errors:
        print(f"ERROR {error}")
    print(
        f"docs: {len(files)} Markdown files, {checked} relative links checked, "
        f"{len(errors)} broken links or wiki-map errors"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
