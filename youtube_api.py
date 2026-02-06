from googleapiclient.discovery import build

from config import YOUTUBE_API_KEY
from models import ChannelInfo


def _build_client():
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def enrich_channels(channels: list[ChannelInfo]) -> list[ChannelInfo]:
    """
    Enhance channel data with YouTube Data API v3 exact stats.
    Batches up to 50 channel IDs per request for quota efficiency.
    """
    if not YOUTUBE_API_KEY:
        return channels

    youtube = _build_client()
    channel_ids = [ch.channel_id for ch in channels]
    stats_map: dict[str, dict] = {}

    # Batch fetch channel statistics (max 50 per call)
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i + 50]
        response = youtube.channels().list(
            part="statistics,snippet",
            id=",".join(batch),
        ).execute()

        for item in response.get("items", []):
            cid = item["id"]
            stats = item.get("statistics", {})
            stats_map[cid] = {
                "subscriber_count": int(stats.get("subscriberCount", 0)),
                "total_views": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
            }

    # Enrich each channel with API data
    enriched = []
    for ch in channels:
        api_stats = stats_map.get(ch.channel_id)
        if api_stats:
            ch.subscriber_count = api_stats["subscriber_count"]
            ch.total_views = api_stats["total_views"]
            ch.video_count = api_stats["video_count"]

        # Fetch avg views from recent uploads if not already computed
        if ch.avg_views is None:
            ch.avg_views = _fetch_avg_views(youtube, ch.channel_id)

        enriched.append(ch)

    return enriched


def _fetch_avg_views(youtube, channel_id: str, max_videos: int = 10) -> int | None:
    """Fetch exact view counts for recent videos via API."""
    try:
        # Get uploads playlist
        ch_resp = youtube.channels().list(
            part="contentDetails",
            id=channel_id,
        ).execute()

        items = ch_resp.get("items", [])
        if not items:
            return None

        uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # Get recent video IDs
        pl_resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_id,
            maxResults=max_videos,
        ).execute()

        video_ids = [
            item["contentDetails"]["videoId"]
            for item in pl_resp.get("items", [])
        ]

        if not video_ids:
            return None

        # Get view counts
        vid_resp = youtube.videos().list(
            part="statistics",
            id=",".join(video_ids),
        ).execute()

        views = [
            int(item["statistics"].get("viewCount", 0))
            for item in vid_resp.get("items", [])
        ]

        return int(sum(views) / len(views)) if views else None

    except Exception:
        return None
