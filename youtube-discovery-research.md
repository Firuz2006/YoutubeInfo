# YouTube Channel Discovery Tool - Technical Research

**Date**: 2026-02-06
**Focus**: Quota-efficient channel discovery with 10,000 units/day limit

---

## Executive Summary

For a YouTube channel discovery tool with 10,000 quota units/day, the optimal approach is:

1. **Use yt-dlp for initial discovery** (no quota cost) to find channel IDs
2. **Use YouTube Data API v3 sparingly** for accurate statistics
3. **Cache aggressively** - channel stats change slowly
4. **Use OpenAI GPT-4 mini** for partnership fit descriptions (cheap, effective)

With this hybrid approach, you can analyze **~90 channels/day** using official API, or **unlimited channels** using yt-dlp only with slightly less accurate data.

---

## YouTube Data API v3: Endpoints & Quota Costs

### Quota Allocation
- **Daily limit**: 10,000 units
- **Reset time**: Midnight Pacific Time
- **Cost applies**: Even to invalid requests

### Required Endpoints

#### 1. search.list - Find Channels by Text Query
**Cost**: 100 units per request
**Purpose**: Search for channels matching a text query

```python
# Request
GET https://www.googleapis.com/youtube/v3/search
  ?part=snippet
  &q=python+programming
  &type=channel
  &maxResults=50

# Response includes
{
  "items": [{
    "id": {"channelId": "UC8butISFwT-Wl7EV0hUK0BQ"},
    "snippet": {
      "channelTitle": "freeCodeCamp.org",
      "description": "...",
      "thumbnails": {...}
    }
  }]
}
```

**Key parameters**:
- `type=channel` - Only return channels
- `maxResults` - Up to 50 results per page (default 5)
- `pageToken` - For pagination (each page costs 100 units)

**Quota impact**:
- 1 search = 100 units
- Max 100 searches/day = entire quota
- **Recommendation**: Use sparingly, cache results

#### 2. channels.list - Get Channel Statistics
**Cost**: 1 unit per request
**Purpose**: Get subscriber count, view count, video count

```python
# Request (batch up to 50 channel IDs)
GET https://www.googleapis.com/youtube/v3/channels
  ?part=snippet,statistics
  &id=UC8butISFwT-Wl7EV0hUK0BQ,UC_x5XG1OV2P6uZZ5FSM9Ttw

# Response includes
{
  "items": [{
    "id": "UC8butISFwT-Wl7EV0hUK0BQ",
    "snippet": {"title": "freeCodeCamp.org", ...},
    "statistics": {
      "subscriberCount": "10500000",
      "viewCount": "580000000",
      "videoCount": "1520",
      "hiddenSubscriberCount": false
    }
  }]
}
```

**Key optimization**: Batch up to 50 channel IDs per request
- 1 request = 1 unit for 50 channels
- 9,900 remaining units = 495,000 channels/day (theoretical max)

**Part parameters** (no extra cost):
- `snippet` - Title, description, thumbnails
- `statistics` - Subscriber/view/video counts
- `contentDetails` - Upload playlist ID
- `topicDetails` - Freebase topic categories

#### 3. videos.list - Get Video Statistics
**Cost**: 1 unit per request
**Purpose**: Get view counts for recent videos to calculate average

```python
# Request (batch up to 50 video IDs)
GET https://www.googleapis.com/youtube/v3/videos
  ?part=statistics
  &id=video_id_1,video_id_2,video_id_3

# Response includes
{
  "items": [{
    "id": "video_id_1",
    "statistics": {
      "viewCount": "120000",
      "likeCount": "5000",
      "commentCount": "350"
    }
  }]
}
```

**Key optimization**: Batch up to 50 video IDs per request

---

## Quota-Efficient Workflow

### Option A: API-Only Approach (90 channels/day)

**Daily quota allocation**:
- 1 search query = 100 units
- 90 channels.list calls = 90 units (get stats)
- 90 videos.list calls = 90 units (get recent video stats)
- **Total**: 280 units per full workflow

**Steps**:
1. Search for channels: `search.list` (100 units) → Get 50 channel IDs
2. Get channel stats: `channels.list` with batching (1-2 units for 50 channels)
3. Get video IDs from upload playlist: Use `contentDetails.relatedPlaylists.uploads`
4. Get video stats: `videos.list` with batching (1-2 units for 50 videos)

**Reality check**: You can do ~35 full workflows per day (35 searches × 50 results = 1,750 channels)

### Option B: Hybrid Approach (Unlimited channels, cached data)

**Use yt-dlp for discovery** (no quota cost):
```python
import yt_dlp

# Search for channels (no quota cost)
ydl_opts = {
    'quiet': True,
    'extract_flat': True,  # Don't download videos
    'skip_download': True
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    result = ydl.extract_info(f"ytsearch50:python programming", download=False)
    channels = [entry['channel_id'] for entry in result['entries']]
```

**Use API only for accurate stats**:
- Channel statistics change slowly (update daily/weekly)
- Cache channel stats for 7 days
- Only use API quota for new/outdated channels

**Quota savings**:
- No search.list calls (save 100 units per search)
- Only channels.list for new channels (1 unit per 50 channels)
- Reserve quota for video stats if needed

---

## Alternative Approaches: Pros & Cons

### yt-dlp (Recommended for Discovery)

**Pros**:
- No quota limits
- Fast metadata extraction
- Can extract channel info, video lists, view counts
- Works without API key
- Actively maintained (fork of youtube-dl)

**Cons**:
- Web scraping - subject to breakage if YouTube changes HTML
- Less reliable than official API
- Rate limiting from YouTube's side (use delays)
- Cannot extract all statistics (e.g., exact subscriber count may be rounded)

**Best for**:
- Initial channel discovery
- Getting video lists
- Extracting metadata when API quota exhausted

**Python example**:
```python
import yt_dlp

def get_channel_videos(channel_url):
    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',  # Don't download, just extract metadata
        'skip_download': True,
        'playlistend': 10  # Limit to recent 10 videos
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
        return {
            'channel_id': info.get('channel_id'),
            'channel': info.get('channel'),
            'subscriber_count': info.get('channel_follower_count'),  # May be approximate
            'videos': [
                {
                    'id': entry['id'],
                    'title': entry['title'],
                    'view_count': entry.get('view_count', 0)
                }
                for entry in info['entries'][:10]
            ]
        }
```

### scrapetube

**Pros**:
- Lightweight, pure Python
- No dependencies
- Designed specifically for channel/playlist scraping
- Returns generator (memory efficient)

**Cons**:
- Limited to scraping, no metadata beyond basic fields
- May break with YouTube changes
- Slower than yt-dlp
- Less actively maintained

**Best for**:
- Simple video list extraction
- Low-dependency environments

**Python example**:
```python
import scrapetube

# Get videos from channel
videos = scrapetube.get_channel("UCuAXFkgsw1L7xaCfnd5JJOw")
for video in videos:
    print(video['videoId'], video['title']['runs'][0]['text'])
```

### youtube-search-python

**Pros**:
- Pure Python, no API key needed
- Simple API for searching
- Returns structured data

**Cons**:
- Deprecated/unmaintained
- Scraping-based (fragile)
- Slower than yt-dlp

**Best for**:
- Nothing - use yt-dlp instead

---

## Best Python Libraries

### 1. google-api-python-client (Official, Recommended for API)

**Installation**:
```bash
pip install google-api-python-client google-auth-oauthlib
```

**Pros**:
- Official Google library
- Well-documented
- Supports all YouTube API endpoints
- Type hints, auto-completion

**Cons**:
- Verbose syntax
- Requires API key management
- Quota limits apply

**Example**:
```python
from googleapiclient.discovery import build

API_KEY = "your_api_key"
youtube = build('youtube', 'v3', developerKey=API_KEY)

# Search for channels
request = youtube.search().list(
    part="snippet",
    q="python programming",
    type="channel",
    maxResults=50
)
response = request.execute()

# Get channel statistics (batch 50 IDs)
channel_ids = [item['id']['channelId'] for item in response['items']]
channels_request = youtube.channels().list(
    part="snippet,statistics",
    id=",".join(channel_ids)
)
channels_response = channels_request.execute()
```

### 2. yt-dlp (Recommended for Quota-Free Discovery)

**Installation**:
```bash
pip install yt-dlp
```

**Example** (see above)

### 3. pyyoutube (python-youtube) - Wrapper Alternative

**Installation**:
```bash
pip install python-youtube
```

**Pros**:
- Cleaner syntax than google-api-python-client
- Object-oriented API
- Built-in pagination handling

**Cons**:
- Less feature-complete than official library
- Smaller community

**Example**:
```python
from pyyoutube import Client

client = Client(api_key="your_api_key")

# Search channels
search = client.search.list(q="python programming", search_type="channel", count=50)

# Get channel stats
channel = client.channels.list(channel_id="UC8butISFwT-Wl7EV0hUK0BQ")
print(channel.items[0].statistics.subscriberCount)
```

---

## Efficiently Calculate Average Views Per Video

### Problem
Getting average views requires:
1. Getting list of video IDs (from channel's upload playlist)
2. Getting view counts for each video

### Quota-Efficient Strategy

**Step 1: Get upload playlist ID** (1 unit, batch 50 channels)
```python
channels = youtube.channels().list(
    part="contentDetails",
    id=",".join(channel_ids)  # Up to 50 IDs
).execute()

upload_playlist_id = channels['items'][0]['contentDetails']['relatedPlaylists']['uploads']
```

**Step 2: Get recent video IDs** (1 unit per 50 videos)
```python
# Get last 10 videos from upload playlist
playlist_items = youtube.playlistItems().list(
    part="contentDetails",
    playlistId=upload_playlist_id,
    maxResults=10  # Only recent videos for average
).execute()

video_ids = [item['contentDetails']['videoId'] for item in playlist_items['items']]
```

**Step 3: Get video statistics** (1 unit per 50 videos)
```python
# Batch request for video stats
videos = youtube.videos().list(
    part="statistics",
    id=",".join(video_ids)
).execute()

view_counts = [int(video['statistics']['viewCount']) for video in videos['items']]
average_views = sum(view_counts) / len(view_counts)
```

**Total quota cost per channel**: 3 units (if batching)
**Total quota cost without batching**: 3 units per channel = 3,333 channels/day max

### Optimization: Use yt-dlp for Video Lists

```python
import yt_dlp

def get_channel_avg_views(channel_id):
    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'playlistend': 10  # Last 10 videos
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Extract from channel's video tab
        info = ydl.extract_info(f"https://www.youtube.com/@channelname/videos", download=False)

        view_counts = [entry.get('view_count', 0) for entry in info['entries'][:10]]
        return sum(view_counts) / len(view_counts) if view_counts else 0
```

**Quota cost**: 0 units (but slower, may be less accurate)

---

## Using OpenAI/GPT API for Partnership Fit Descriptions

### Goal
Generate natural language descriptions of why a channel is a good partnership fit based on:
- Channel niche/topic
- Audience size
- Engagement metrics
- Content type

### Recommended Approach: GPT-4o-mini

**Why GPT-4o-mini**:
- Cost: $0.15/1M input tokens, $0.60/1M output tokens
- Fast inference
- Good enough for simple text generation
- Structured output support

**Installation**:
```bash
pip install openai
```

**Example: Generate Partnership Fit Description**

```python
from openai import OpenAI
from pydantic import BaseModel
from typing import List

client = OpenAI(api_key="your_openai_api_key")

class PartnershipFit(BaseModel):
    summary: str  # 1-2 sentence overview
    strengths: List[str]  # 3-5 bullet points
    audience_match: str  # Why audience is a good fit
    recommendation: str  # Partner/Pass/Maybe

def generate_partnership_description(channel_data: dict) -> PartnershipFit:
    """
    Generate partnership fit analysis using GPT-4o-mini

    Args:
        channel_data: Dict with keys:
            - channel_name: str
            - niche: str (detected from video titles/topics)
            - subscriber_count: int
            - avg_views: int
            - video_count: int
            - top_video_topics: List[str]
    """

    prompt = f"""Analyze this YouTube channel for partnership potential:

Channel: {channel_data['channel_name']}
Niche: {channel_data['niche']}
Subscribers: {channel_data['subscriber_count']:,}
Average Views: {channel_data['avg_views']:,}
Total Videos: {channel_data['video_count']}
Top Topics: {', '.join(channel_data['top_video_topics'])}

Provide partnership analysis with:
1. Brief summary (1-2 sentences)
2. Key strengths (3-5 points)
3. Audience match analysis
4. Recommendation (Partner/Pass/Maybe)
"""

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a YouTube partnership analyst. Provide concise, data-driven partnership recommendations."},
            {"role": "user", "content": prompt}
        ],
        response_format=PartnershipFit
    )

    return completion.choices[0].message.parsed

# Example usage
channel = {
    'channel_name': 'freeCodeCamp.org',
    'niche': 'Programming Education',
    'subscriber_count': 10_500_000,
    'avg_views': 150_000,
    'video_count': 1520,
    'top_video_topics': ['Python tutorials', 'Web development', 'Data science', 'JavaScript']
}

result = generate_partnership_description(channel)
print(f"Summary: {result.summary}")
print(f"Strengths: {result.strengths}")
print(f"Recommendation: {result.recommendation}")
```

**Cost estimate**:
- Input: ~200 tokens per channel = $0.00003 per channel
- Output: ~150 tokens per channel = $0.00009 per channel
- **Total**: ~$0.00012 per channel = 8,333 channels for $1

### Alternative: Determine Niche/Topic with GPT

```python
from openai import OpenAI
from pydantic import BaseModel
from typing import List

class ChannelNiche(BaseModel):
    primary_niche: str  # Main topic category
    sub_niches: List[str]  # Secondary topics (2-3)
    content_type: str  # Tutorial, Entertainment, News, Review, etc.

def detect_channel_niche(video_titles: List[str]) -> ChannelNiche:
    """
    Detect channel niche from video titles using GPT

    Args:
        video_titles: List of recent video titles (10-20 videos)
    """

    titles_text = "\n".join(f"- {title}" for title in video_titles)

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a YouTube content categorization expert. Analyze video titles to determine channel niche."},
            {"role": "user", "content": f"Categorize this channel based on video titles:\n\n{titles_text}"}
        ],
        response_format=ChannelNiche
    )

    return completion.choices[0].message.parsed

# Example
titles = [
    "Python Full Course for Beginners",
    "JavaScript Tutorial - Learn JS in 3 Hours",
    "React Course for Beginners",
    "Web Development Bootcamp 2024"
]

niche = detect_channel_niche(titles)
print(f"Niche: {niche.primary_niche}")
print(f"Sub-niches: {niche.sub_niches}")
print(f"Type: {niche.content_type}")
```

---

## Concrete Recommendations

### 1. Architecture: Hybrid Approach

```
┌─────────────────────────────────────────────┐
│ YouTube Channel Discovery Tool              │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│ Discovery Layer (yt-dlp)                    │
│ • Search for channels (no quota)            │
│ • Extract video lists (no quota)            │
│ • Get approximate stats (no quota)          │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│ Cache Layer (SQLite/Redis)                  │
│ • Store channel stats (TTL: 7 days)         │
│ • Store video stats (TTL: 1 day)            │
│ • Deduplicate API calls                     │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│ API Layer (google-api-python-client)        │
│ • Accurate stats for new channels (1 unit)  │
│ • Batch requests (50 IDs per call)          │
│ • Fallback when yt-dlp fails                │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│ Analysis Layer (OpenAI GPT-4o-mini)         │
│ • Detect channel niche from titles          │
│ • Generate partnership fit descriptions     │
│ • Structured output with Pydantic           │
└─────────────────────────────────────────────┘
```

### 2. Quota Budget Allocation

**Daily quota**: 10,000 units

**Allocation**:
- 500 units: Emergency search queries (5 searches)
- 9,000 units: Channel stats requests (9,000 channels or 450,000 if batched perfectly)
- 500 units: Video stats requests (fallback if yt-dlp fails)

**Strategy**:
- Use yt-dlp for 95% of operations
- Reserve API for accurate subscriber counts and when yt-dlp fails
- Batch aggressively (50 IDs per request)

### 3. Implementation Checklist

**Setup**:
- [ ] Install dependencies: `pip install yt-dlp google-api-python-client openai pydantic`
- [ ] Get YouTube Data API key from Google Cloud Console
- [ ] Get OpenAI API key
- [ ] Set up SQLite cache database

**Core functions**:
- [ ] `search_channels(query: str) -> List[str]` - Use yt-dlp
- [ ] `get_channel_stats(channel_ids: List[str]) -> List[dict]` - Use API with caching
- [ ] `get_recent_videos(channel_id: str) -> List[dict]` - Use yt-dlp
- [ ] `calculate_avg_views(videos: List[dict]) -> float` - Local calculation
- [ ] `detect_niche(video_titles: List[str]) -> str` - Use GPT-4o-mini
- [ ] `generate_partnership_fit(channel_data: dict) -> str` - Use GPT-4o-mini

**Error handling**:
- [ ] Retry logic for rate limits (exponential backoff)
- [ ] Fallback to API if yt-dlp fails
- [ ] Quota tracking (log API usage)
- [ ] Handle private/deleted channels gracefully

### 4. Code Template

```python
import yt_dlp
from googleapiclient.discovery import build
from openai import OpenAI
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pydantic import BaseModel

# Configuration
YOUTUBE_API_KEY = "your_youtube_api_key"
OPENAI_API_KEY = "your_openai_api_key"
CACHE_DB = "youtube_cache.db"

# Initialize clients
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Cache setup
def init_cache():
    conn = sqlite3.connect(CACHE_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS channel_stats
                 (channel_id TEXT PRIMARY KEY, data TEXT, cached_at TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_cached_stats(channel_id: str, ttl_days: int = 7) -> Optional[dict]:
    conn = sqlite3.connect(CACHE_DB)
    c = conn.cursor()
    cutoff = datetime.now() - timedelta(days=ttl_days)
    c.execute("SELECT data FROM channel_stats WHERE channel_id = ? AND cached_at > ?",
              (channel_id, cutoff))
    row = c.fetchone()
    conn.close()
    return eval(row[0]) if row else None

def cache_stats(channel_id: str, data: dict):
    conn = sqlite3.connect(CACHE_DB)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO channel_stats VALUES (?, ?, ?)",
              (channel_id, str(data), datetime.now()))
    conn.commit()
    conn.close()

# Discovery: Use yt-dlp (no quota)
def search_channels_ytdlp(query: str, max_results: int = 50) -> List[str]:
    """Search for channels using yt-dlp (no API quota)"""
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        # Extract unique channel IDs
        channels = {}
        for entry in result.get('entries', []):
            ch_id = entry.get('channel_id')
            if ch_id and ch_id not in channels:
                channels[ch_id] = {
                    'channel_id': ch_id,
                    'channel_name': entry.get('channel'),
                    'url': entry.get('channel_url')
                }
        return list(channels.values())

# Stats: Use API with caching (1 unit per 50 channels)
def get_channel_stats_api(channel_ids: List[str]) -> List[dict]:
    """Get accurate channel stats from YouTube API"""
    # Filter out cached channels
    uncached_ids = [cid for cid in channel_ids if not get_cached_stats(cid)]

    if not uncached_ids:
        return [get_cached_stats(cid) for cid in channel_ids]

    # Batch request (50 IDs max per call)
    results = []
    for i in range(0, len(uncached_ids), 50):
        batch = uncached_ids[i:i+50]
        response = youtube.channels().list(
            part="snippet,statistics",
            id=",".join(batch)
        ).execute()

        for item in response['items']:
            data = {
                'channel_id': item['id'],
                'title': item['snippet']['title'],
                'subscribers': int(item['statistics']['subscriberCount']),
                'views': int(item['statistics']['viewCount']),
                'video_count': int(item['statistics']['videoCount'])
            }
            cache_stats(item['id'], data)
            results.append(data)

    # Add cached results
    cached = [get_cached_stats(cid) for cid in channel_ids if get_cached_stats(cid)]
    return results + cached

# Video analysis: Use yt-dlp (no quota)
def get_recent_videos_ytdlp(channel_url: str, count: int = 10) -> List[dict]:
    """Get recent videos from channel using yt-dlp"""
    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'playlistend': count
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"{channel_url}/videos", download=False)
        return [
            {
                'video_id': entry['id'],
                'title': entry['title'],
                'views': entry.get('view_count', 0)
            }
            for entry in info.get('entries', [])[:count]
        ]

# Niche detection: Use GPT-4o-mini
class ChannelNiche(BaseModel):
    primary_niche: str
    content_type: str

def detect_niche(video_titles: List[str]) -> ChannelNiche:
    titles_text = "\n".join(f"- {title}" for title in video_titles)

    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Categorize YouTube channel by video titles."},
            {"role": "user", "content": f"Titles:\n{titles_text}"}
        ],
        response_format=ChannelNiche
    )

    return completion.choices[0].message.parsed

# Main workflow
def discover_channels(query: str, max_results: int = 50):
    init_cache()

    # Step 1: Search (no quota, yt-dlp)
    print(f"Searching for channels: {query}")
    channels = search_channels_ytdlp(query, max_results)
    print(f"Found {len(channels)} channels")

    # Step 2: Get accurate stats (1 unit per 50 channels, API)
    print("Fetching channel statistics...")
    channel_ids = [ch['channel_id'] for ch in channels]
    stats = get_channel_stats_api(channel_ids)

    # Step 3: Analyze top channels
    results = []
    for ch, stat in zip(channels[:10], stats[:10]):  # Top 10 only
        print(f"\nAnalyzing: {ch['channel_name']}")

        # Get recent videos (no quota, yt-dlp)
        videos = get_recent_videos_ytdlp(ch['url'])
        avg_views = sum(v['views'] for v in videos) / len(videos) if videos else 0

        # Detect niche (OpenAI)
        niche = detect_niche([v['title'] for v in videos])

        results.append({
            'channel': ch['channel_name'],
            'subscribers': stat['subscribers'],
            'avg_views': avg_views,
            'niche': niche.primary_niche,
            'content_type': niche.content_type
        })

    return results

# Example usage
if __name__ == "__main__":
    results = discover_channels("python programming", max_results=50)

    for r in results:
        print(f"\n{r['channel']}")
        print(f"  Subscribers: {r['subscribers']:,}")
        print(f"  Avg Views: {r['avg_views']:,.0f}")
        print(f"  Niche: {r['niche']}")
        print(f"  Type: {r['content_type']}")
```

---

## Cost Analysis

### YouTube API Costs
- **Free tier**: 10,000 units/day
- **Cost per channel** (with optimization): 0.02 units (batching 50 channels)
- **Channels per day**: ~450,000 (if only getting stats)
- **Realistic usage**: ~5,000 channels/day (including searches, video stats)

### OpenAI API Costs (GPT-4o-mini)
- **Input**: $0.15/1M tokens
- **Output**: $0.60/1M tokens
- **Per channel analysis**: ~$0.00012
- **1,000 channels**: ~$0.12

### Total Cost
- YouTube API: $0 (within free tier for most use cases)
- OpenAI API: ~$0.12 per 1,000 channels
- **Very affordable** for channel discovery tool

---

## Sources

- [YouTube Data API Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost)
- [YouTube API Costs and Limits Guide](https://www.getphyllo.com/post/is-the-youtube-api-free-costs-limits-iv)
- [Complete Guide to YouTube Data API v3](https://elfsight.com/blog/youtube-data-api-v3-limits-operations-resources-methods-etc/)
- [YouTube Data API Complete Tutorial 2026](https://getlate.dev/blog/youtube-api)
- [yt-dlp for YouTube Scraping](https://oxylabs.io/blog/how-to-scrape-youtube)
- [Python YouTube API Libraries Comparison](https://pypi.org/project/python-youtube/)
- [Best YouTube Scrapers 2026](https://medium.com/@datajournal/best-youtube-scrapers-5c3f9513c7ea)
- [How to Scrape YouTube in 2026](https://roundproxies.com/blog/scrape-youtube/)
