#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_readme_index.py — Rebuild the "## 內容索引" section of README.md from
data/{channel}/{stem}_keyframes.md files.

Two-level index: channel (linked to data/{channel}/) -> videos (linked to their
_keyframes.md, with title + upload date). Title/date come from yt-dlp and are
cached in data/.video_metadata.json so re-runs only look up genuinely new videos
(and generation still succeeds, using stale cached data, if a lookup is flaky).

Usage:
    python scripts/generate_readme_index.py [--readme README.md]

Intended to run in CI (see .github/workflows/update-readme-index.yml) whenever a
new/changed data/**/*_keyframes.md lands on main, but is safe to run locally too.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
CACHE_PATH = DATA_DIR / ".video_metadata.json"
HEADER = "## 內容索引"

VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}$")

YT_DLP_ARGS = ["--js-runtimes", "node", "--remote-components", "ejs:github"]


def load_cache() -> dict[str, dict[str, str]]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict[str, dict[str, str]]) -> None:
    CACHE_PATH.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def fetch_video_meta(video_id: str) -> dict[str, str] | None:
    """{'title': ..., 'date': 'YYYY-MM-DD', 'channel_name': ...} via yt-dlp, or None if
    the lookup fails (deleted/private video, transient network/anti-bot flakiness, etc.).
    channel_name is the channel's real display name (e.g. "游庭皓的財經皓角"), not our
    URL-handle-derived slug (e.g. "yutinghaofinance") — used for a more readable header."""
    proc = subprocess.run(
        ["yt-dlp", *YT_DLP_ARGS, "--skip-download", "--print", "%(title)s|||%(upload_date)s|||%(channel)s",
         f"https://www.youtube.com/watch?v={video_id}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        print(f"[generate_readme_index]   metadata lookup failed for {video_id}: {proc.stderr[:200]}")
        return None
    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    if line.count("|||") != 2:
        return None
    title, upload_date, channel_name = line.split("|||")
    date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}" if len(upload_date) == 8 else upload_date
    return {"title": title.strip(), "date": date, "channel_name": channel_name.strip()}


def build_index() -> dict[str, list[dict]]:
    """{channel: [{stem, video_id, title, date, md_path}, ...]}, videos sorted newest first."""
    cache = load_cache()
    by_channel: dict[str, list[dict]] = {}

    for md_path in sorted(DATA_DIR.glob("*/*_keyframes.md")):
        channel = md_path.parent.name
        stem = md_path.name[: -len("_keyframes.md")]
        m = VIDEO_ID_RE.search(stem)
        if not m:
            continue
        video_id = m.group(0)

        meta = cache.get(video_id)
        if meta is None or "channel_name" not in meta:
            # Also refetch entries cached before channel_name was tracked, so existing
            # stems get backfilled with a readable channel name on the next CI run.
            print(f"[generate_readme_index] fetching metadata for {video_id} ({stem})")
            fetched = fetch_video_meta(video_id)
            if fetched is not None:
                meta = fetched
                cache[video_id] = meta
        if meta is None:
            # Lookup failed and nothing cached — still list it, just without title/date,
            # rather than silently dropping a video that does have a keyframes.md.
            meta = {"title": stem, "date": "", "channel_name": channel}

        by_channel.setdefault(channel, []).append({
            "stem": stem,
            "video_id": video_id,
            "title": meta["title"],
            "date": meta["date"],
            "channel_name": meta.get("channel_name", channel),
            "md_path": md_path.relative_to(REPO_ROOT).as_posix(),
        })

    save_cache(cache)

    for videos in by_channel.values():
        videos.sort(key=lambda v: v["date"], reverse=True)
    return by_channel


def render_index(by_channel: dict[str, list[dict]]) -> str:
    if not by_channel:
        return f"{HEADER}\n\n*(尚無已完成關鍵畫面擷取的影片)*\n"

    lines = [HEADER, ""]
    for channel in sorted(by_channel):
        videos = by_channel[channel]
        display_name = videos[0]["channel_name"] or channel
        lines.append(f"### [{display_name}](data/{channel}/)")
        lines.append("")
        lines.append("| 影片 | 日期 |")
        lines.append("| --- | --- |")
        for v in by_channel[channel]:
            title = v["title"].replace("|", "\\|")
            lines.append(f"| [{title}]({v['md_path']}) | {v['date']} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def update_readme(readme_path: Path, section: str) -> bool:
    """Replace the HEADER..next('## '|EOF) block in-place. Returns True if changed."""
    content = readme_path.read_text(encoding="utf-8")
    if HEADER in content:
        start = content.index(HEADER)
        rest = content[start + len(HEADER):]
        m = re.search(r"\n## ", rest)
        end = start + len(HEADER) + (m.start() if m else len(rest))
        new_content = content[:start].rstrip() + "\n\n" + section.rstrip() + "\n\n" + content[end:].lstrip()
    else:
        new_content = content.rstrip() + "\n\n" + section.rstrip() + "\n"
    if new_content == content:
        return False
    readme_path.write_text(new_content, encoding="utf-8")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", default=str(REPO_ROOT / "README.md"))
    args = parser.parse_args()

    index = build_index()
    section = render_index(index)
    changed = update_readme(Path(args.readme), section)
    total_videos = sum(len(v) for v in index.values())
    print(f"[generate_readme_index] {len(index)} channel(s), {total_videos} video(s) — README {'updated' if changed else 'unchanged'}")
