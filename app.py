import csv
import io
import json
import threading
import uuid

from flask import Flask, render_template, request, jsonify, Response

import config
from ai_analyzer import analyze_channels
from models import ChannelReport
from youtube_api import enrich_channels
from youtube_searcher import search_channels

app = Flask(__name__)

# In-memory task storage
tasks: dict[str, dict] = {}


def _run_search(task_id: str, query: str, max_results: int, skip_ai: bool):
    task = tasks[task_id]
    try:
        task["status"] = "searching"
        task["message"] = f"Searching YouTube for: {query}"

        done_count = 0
        total_count = 0

        def on_progress(cid, name, state):
            nonlocal done_count, total_count
            if state == "fetching":
                total_count += 1
                task["message"] = f"Fetching channel {total_count}: {name}"
            elif state == "done":
                done_count += 1
                task["message"] = f"Fetched {done_count} channels..."

        channels = search_channels(query, max_results, on_progress=on_progress)
        if not channels:
            task["status"] = "done"
            task["message"] = "No channels found"
            task["results"] = []
            return

        task["message"] = f"Found {len(channels)} channels"

        if config.has_youtube_api():
            task["status"] = "enriching"
            task["message"] = "Enriching with YouTube Data API..."
            channels = enrich_channels(channels)

        analyses = []
        if not skip_ai and config.OPENAI_API_KEY:
            task["status"] = "analyzing"
            task["message"] = "Analyzing channels with GPT-4o-mini..."
            analyses = analyze_channels(channels)

        analysis_map = {a.channel_id: a for a in analyses}
        reports = [
            ChannelReport(channel=ch, analysis=analysis_map.get(ch.channel_id))
            for ch in channels
        ]

        task["results"] = [r.model_dump() for r in reports]
        task["status"] = "done"
        task["message"] = f"Done. Found {len(reports)} channels."

    except Exception as e:
        task["status"] = "error"
        task["message"] = str(e)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/search", methods=["POST"])
def api_search():
    data = request.get_json()
    query = data.get("query", "").strip()
    max_results = data.get("max_results", 200)
    skip_ai = data.get("skip_ai", False)

    if not query:
        return jsonify({"error": "Query is required"}), 400

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "queued",
        "message": "Starting search...",
        "results": [],
    }

    thread = threading.Thread(
        target=_run_search,
        args=(task_id, query, max_results, skip_ai),
        daemon=True,
    )
    thread.start()

    return jsonify({"task_id": task_id})


@app.route("/api/status/<task_id>")
def api_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task)


@app.route("/api/csv/<task_id>")
def api_csv(task_id):
    task = tasks.get(task_id)
    if not task or not task.get("results"):
        return jsonify({"error": "No results"}), 404

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Channel", "URL", "Subscribers", "Avg Views", "Video Count", "Niche", "Why Partner Fit"])

    for r in task["results"]:
        ch = r["channel"]
        analysis = r.get("analysis") or {}
        writer.writerow([
            ch.get("name", ""),
            ch.get("url", ""),
            ch.get("subscriber_count", ""),
            ch.get("avg_views", ""),
            ch.get("video_count", ""),
            analysis.get("niche", ""),
            analysis.get("why_partner_fit", ""),
        ])

    csv_content = output.getvalue()
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=results_{task_id[:8]}.csv"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
