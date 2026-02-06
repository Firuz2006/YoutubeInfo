import json

from openai import OpenAI
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import OPENAI_API_KEY
from models import AnalysisResult, ChannelInfo

SYSTEM_PROMPT = """You are an expert analyst for Higgsfield AI — a company that builds AI-powered video generation tools for creators and brands.

Your task: for each YouTube channel provided, determine:
1. `niche` — 1-2 word topic classification (e.g. "tech reviews", "travel vlog", "gaming", "auto", "beauty", "cooking")
2. `why_partner_fit` — 2-3 sentences explaining why this channel would be a good partner for Higgsfield AI. Consider:
   - How AI video tools could enhance their content workflow
   - Their audience overlap with Higgsfield AI's target market
   - Specific content formats that could benefit from AI generation

Respond in the same language as the channel's content. If channel titles are in Russian, respond in Russian.

Return a JSON array of objects with keys: channel_id, niche, why_partner_fit"""

_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "channel_analyses",
        "schema": {
            "type": "object",
            "properties": {
                "analyses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "channel_id": {"type": "string"},
                            "niche": {"type": "string"},
                            "why_partner_fit": {"type": "string"},
                        },
                        "required": ["channel_id", "niche", "why_partner_fit"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["analyses"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


def _build_channel_summary(channels: list[ChannelInfo]) -> str:
    lines = []
    for ch in channels:
        parts = [f"Channel: {ch.name} (ID: {ch.channel_id})"]
        if ch.subscriber_count:
            parts.append(f"  Subscribers: {ch.subscriber_count:,}")
        if ch.avg_views:
            parts.append(f"  Avg views: {ch.avg_views:,}")
        if ch.recent_video_titles:
            titles = "; ".join(ch.recent_video_titles[:5])
            parts.append(f"  Recent videos: {titles}")
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def analyze_channels(channels: list[ChannelInfo]) -> list[AnalysisResult]:
    """Send all channels to GPT-4o-mini in a single batch and parse structured output."""
    if not channels:
        return []

    client = OpenAI(api_key=OPENAI_API_KEY)
    summary = _build_channel_summary(channels)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task("Analyzing channels with GPT-4o-mini...", total=None)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze these YouTube channels:\n\n{summary}"},
            ],
            response_format=_RESPONSE_SCHEMA,
            temperature=0.3,
        )

    content = response.choices[0].message.content
    data = json.loads(content)
    analyses = data.get("analyses", [])

    return [AnalysisResult(**item) for item in analyses]
