import json
import subprocess
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import ChannelInfo


def _run_ytdlp(args: list[str], timeout: int = 120) -> str | None:
    try:
        result = subprocess.run(
            ["yt-dlp", *args],
            capture_output=True, text=True, timeout=timeout, encoding="utf-8"
        )
        return result.stdout if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _search_videos(query: str, max_results: int) -> list[dict]:
    output = _run_ytdlp([
        f"ytsearch{max_results}:{query}",
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        "--quiet",
    ], timeout=300)
    if not output:
        return []

    entries = []
    for line in output.strip().splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _get_channel_videos(channel_url: str, max_videos: int = 10) -> list[dict]:
    output = _run_ytdlp([
        f"{channel_url}/videos",
        "--dump-json",
        "--flat-playlist",
        "--playlist-items", f"1:{max_videos}",
        "--no-warnings",
        "--quiet",
    ])
    if not output:
        return []

    videos = []
    for line in output.strip().splitlines():
        try:
            videos.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return videos


def _extract_channel_id(entry: dict) -> str | None:
    return entry.get("channel_id") or entry.get("uploader_id")


def _process_channel(cid: str, entry: dict, on_progress=None) -> ChannelInfo:
    channel_name = entry.get("channel") or entry.get("uploader") or "Unknown"
    channel_url = entry.get("channel_url") or entry.get("uploader_url") or ""

    if on_progress:
        on_progress(cid, channel_name, "fetching")

    subscriber_count = entry.get("channel_follower_count")

    videos = _get_channel_videos(channel_url) if channel_url else []
    view_counts = [v.get("view_count", 0) for v in videos if v.get("view_count")]
    avg_views = int(sum(view_counts) / len(view_counts)) if view_counts else None
    recent_titles = [v.get("title", "") for v in videos[:10] if v.get("title")]

    info = ChannelInfo(
        channel_id=cid,
        name=channel_name,
        url=channel_url or f"https://www.youtube.com/channel/{cid}",
        subscriber_count=subscriber_count,
        video_count=len(videos) if videos else None,
        avg_views=avg_views,
        recent_video_titles=recent_titles,
    )

    if on_progress:
        on_progress(cid, channel_name, "done")

    return info


def search_channels(query: str, max_results: int = 200, on_progress=None, max_workers: int = 4) -> list[ChannelInfo]:
    search_count = min(max_results * 3, 600)
    entries = _search_videos(query, search_count)

    seen: OrderedDict[str, dict] = OrderedDict()
    for entry in entries:
        cid = _extract_channel_id(entry)
        if cid and cid not in seen:
            seen[cid] = entry
        if len(seen) >= max_results:
            break

    channels: list[ChannelInfo] = []
    order = list(seen.keys())

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_process_channel, cid, entry, on_progress): cid
            for cid, entry in seen.items()
        }
        result_map: dict[str, ChannelInfo] = {}
        for future in as_completed(futures):
            cid = futures[future]
            try:
                result_map[cid] = future.result()
            except Exception:
                pass

    # Preserve discovery order
    channels = [result_map[cid] for cid in order if cid in result_map]
    return channels
