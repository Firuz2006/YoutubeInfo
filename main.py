import argparse
import json
import re
from datetime import datetime

from rich.console import Console
from rich.table import Table

import config
from ai_analyzer import analyze_channels
from models import ChannelReport
from youtube_api import enrich_channels
from youtube_searcher import search_channels

console = Console()


def _format_number(n: int | None) -> str:
    if n is None:
        return "N/A"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _sanitize_filename(s: str) -> str:
    return re.sub(r'[^\w\-]', '_', s)[:50]


def _print_table(reports: list[ChannelReport]):
    table = Table(title="YouTube Channel Discovery", show_lines=True)
    table.add_column("Channel", style="cyan", max_width=25)
    table.add_column("Subs", justify="right", style="green")
    table.add_column("Avg Views", justify="right", style="yellow")
    table.add_column("Niche", style="magenta", max_width=15)
    table.add_column("Why Partner Fit", style="white", max_width=50)

    for r in reports:
        niche = r.analysis.niche if r.analysis else "N/A"
        fit = r.analysis.why_partner_fit if r.analysis else "N/A"
        table.add_row(
            r.channel.name,
            _format_number(r.channel.subscriber_count),
            _format_number(r.channel.avg_views),
            niche,
            fit,
        )

    console.print(table)


def _save_json(reports: list[ChannelReport], query: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"results_{_sanitize_filename(query)}_{timestamp}.json"
    data = [r.model_dump() for r in reports]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"\n[green]Results saved to {filename}[/green]")


def main():
    parser = argparse.ArgumentParser(description="YouTube Channel Discovery Tool")
    parser.add_argument("query", help="Search query for YouTube channels")
    parser.add_argument("--max-results", type=int, default=20, help="Max channels to find (default: 20)")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only, no table")
    parser.add_argument("--no-ai", action="store_true", help="Skip GPT analysis")
    args = parser.parse_args()

    if not args.no_ai:
        config.validate()

    console.print(f"[bold]Searching YouTube for:[/bold] {args.query}")
    console.print(f"[dim]Max results: {args.max_results}[/dim]")

    if not config.has_youtube_api():
        console.print("[dim]YouTube API key not set — using yt-dlp only mode[/dim]")

    # Step 1: Search channels via yt-dlp
    channels = search_channels(args.query, args.max_results)
    if not channels:
        console.print("[red]No channels found.[/red]")
        return

    console.print(f"[green]Found {len(channels)} channels[/green]")

    # Step 2: Enrich with YouTube API if available
    if config.has_youtube_api():
        console.print("[dim]Enriching with YouTube Data API...[/dim]")
        channels = enrich_channels(channels)

    # Step 3: AI analysis
    analyses = []
    if not args.no_ai:
        analyses = analyze_channels(channels)

    # Build reports
    analysis_map = {a.channel_id: a for a in analyses}
    reports = [
        ChannelReport(channel=ch, analysis=analysis_map.get(ch.channel_id))
        for ch in channels
    ]

    # Step 4: Output
    if not args.json_only:
        _print_table(reports)

    _save_json(reports, args.query)


if __name__ == "__main__":
    main()
