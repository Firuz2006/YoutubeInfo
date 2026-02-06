import json
import subprocess
from collections import OrderedDict

from rich.progress import Progress, SpinnerColumn, TextColumn

from models import ChannelInfo


def _run_ytdlp(args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["yt-dlp", *args],
            capture_output=True, text=True, timeout=60, encoding="utf-8"
        )
        return result.stdout if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _search_videos(query: str, max_results: int) -> list[dict]:
    """Search YouTube videos and return raw yt-dlp JSON entries."""
    output = _run_ytdlp([
        f"ytsearch{max_results}:{query}",
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        "--quiet",
    ])
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
    """Fetch recent videos from a channel page."""
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


def search_channels(query: str, max_results: int = 20) -> list[ChannelInfo]:
    """
    Search YouTube for channels matching the query.
    Uses yt-dlp video search, deduplicates by channel, then fetches per-channel stats.
    """
    search_count = max_results * 3  # oversample since multiple videos per channel
    entries = _search_videos(query, search_count)

    # Deduplicate by channel_id, preserving discovery order
    seen: OrderedDict[str, dict] = OrderedDict()
    for entry in entries:
        cid = _extract_channel_id(entry)
        if cid and cid not in seen:
            seen[cid] = entry
        if len(seen) >= max_results:
            break

    channels: list[ChannelInfo] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("Fetching channel data...", total=len(seen))

        for cid, entry in seen.items():
            channel_name = entry.get("channel") or entry.get("uploader") or "Unknown"
            channel_url = entry.get("channel_url") or entry.get("uploader_url") or ""

            progress.update(task, description=f"Fetching: {channel_name}")

            # Get subscriber count from channel metadata if available
            subscriber_count = entry.get("channel_follower_count")

            # Fetch recent videos to compute avg views
            videos = _get_channel_videos(channel_url) if channel_url else []
            view_counts = [v.get("view_count", 0) for v in videos if v.get("view_count")]
            avg_views = int(sum(view_counts) / len(view_counts)) if view_counts else None
            recent_titles = [v.get("title", "") for v in videos[:10] if v.get("title")]

            channels.append(ChannelInfo(
                channel_id=cid,
                name=channel_name,
                url=channel_url or f"https://www.youtube.com/channel/{cid}",
                subscriber_count=subscriber_count,
                video_count=len(videos) if videos else None,
                avg_views=avg_views,
                recent_video_titles=recent_titles,
            ))

            progress.advance(task)

    return channels
