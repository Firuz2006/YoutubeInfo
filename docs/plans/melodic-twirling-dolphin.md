# YouTube Channel Discovery Tool — Implementation Plan

## Context

Build a Python CLI tool that searches YouTube channels by text query, extracts stats, and generates Higgsfield AI partnership fit descriptions using GPT. The tool outputs structured JSON + console table.

## Architecture

```
main.py              — CLI entry point (argparse)
youtube_searcher.py  — yt-dlp channel discovery + video extraction
youtube_api.py       — YouTube Data API v3 (optional, for accurate stats)
ai_analyzer.py       — OpenAI GPT-4o-mini niche + partnership analysis
models.py            — Pydantic models (ChannelInfo, AnalysisResult)
config.py            — .env loading, API key management
```

## Dependencies

```
yt-dlp          — YouTube search & scraping (no API key needed)
google-api-python-client  — YouTube Data API v3 (optional)
openai          — GPT-4o-mini for text generation
pydantic        — Data models & structured output
python-dotenv   — .env file loading
rich            — Console tables & progress bars
```

## Implementation Steps

### Step 1: Project scaffold
- Create `requirements.txt` with dependencies
- Create `.env.example` with `OPENAI_API_KEY=` and `YOUTUBE_API_KEY=` (optional)
- Create `.gitignore` (*.pyc, .env, __pycache__, .venv)
- Create `models.py` with Pydantic models

### Step 2: `youtube_searcher.py` — yt-dlp discovery
- `search_channels(query: str, max_results: int = 20) -> list[ChannelInfo]`
- Uses `yt-dlp` with `ytsearch{N}:{query}` to find videos, extract unique channel IDs
- For each unique channel, fetches channel page via yt-dlp `--dump-json` to get:
  - channel name, url, subscriber_count (approximate)
- Fetches last 10 videos per channel, calculates avg views

### Step 3: `youtube_api.py` — optional accurate stats
- If `YOUTUBE_API_KEY` is set, enhances data with:
  - `channels.list(part=statistics,snippet)` — exact subscribers, total views
  - `playlistItems.list` + `videos.list` — exact video view counts
- Batch requests (50 per call) for quota efficiency
- Falls back to yt-dlp data if no key provided

### Step 4: `ai_analyzer.py` — GPT analysis
- `analyze_channels(channels: list[ChannelInfo]) -> list[AnalysisResult]`
- Single batch prompt with all channel data
- GPT-4o-mini generates for each channel:
  - `niche`: 1-2 word topic classification
  - `why_partner_fit`: 2-3 sentence Higgsfield AI partnership justification
- Structured output via `response_format` with Pydantic schema
- Higgsfield AI context embedded in system prompt

### Step 5: `main.py` — CLI orchestration
- `python main.py "канал про машины"` — basic usage
- `python main.py "тревел-влогеры" --max-results 30` — custom count
- `python main.py "техноблогеры" --json-only` — JSON output only
- Pipeline: search → enrich (optional API) → analyze → output
- Output: JSON file + Rich console table with key metrics

### Step 6: `config.py` — configuration
- Load `.env` via `python-dotenv`
- Validate keys presence
- Warn if no YouTube API key (will use yt-dlp only mode)

## Output Format

Console table (Rich):
```
┌─────────────────┬──────────┬───────────┬────────────┬──────────────────────────┐
│ Channel         │ Subs     │ Avg Views │ Niche      │ Why Partner Fit          │
├─────────────────┼──────────┼───────────┼────────────┼──────────────────────────┤
│ Example Channel │ 1.8M     │ 420K      │ авто       │ Канал делает обзоры...   │
└─────────────────┴──────────┴───────────┴────────────┴──────────────────────────┘
```

JSON output saved to `results_{query}_{timestamp}.json`

## File Paths

All files created in `C:\Users\user\RiderProjects\YoutubeInfo\`:
- `main.py`
- `youtube_searcher.py`
- `youtube_api.py`
- `ai_analyzer.py`
- `models.py`
- `config.py`
- `requirements.txt`
- `.env.example`
- `.gitignore`

## Verification

1. `pip install -r requirements.txt`
2. Create `.env` with `OPENAI_API_KEY=sk-...`
3. `python main.py "техноблогеры"` — should output table + JSON
4. `python main.py "тревел-влогеры" --max-results 10` — smaller result set
5. Verify JSON output file is valid and contains all fields
