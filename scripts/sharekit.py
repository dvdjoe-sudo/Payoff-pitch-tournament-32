#!/usr/bin/env python3
"""Open Graph images, static share pages, and the weekly recap.

Share pages exist because the site routes are hashes. A crawler that
fetches /share/<id>.html can read the title and image, then the page
sends a person to the hash route.
"""

from __future__ import annotations

import html
import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://dvdjoe-sudo.github.io/Payoff-pitch-tournament-32/"


def _publish():
    spec = importlib.util.spec_from_file_location("publish_docs", ROOT / "scripts" / "publish.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def og_png(mod, lines: list[tuple[str, int]]) -> bytes:
    width, height = 1200, 630
    navy = (18, 38, 63)
    gold = (198, 161, 90)
    cream = (246, 241, 230)
    buf = mod._canvas(width, height, navy)
    mod._fill(buf, width, 0, 0, width, 16, gold)
    mod._fill(buf, width, 0, height - 16, width, 16, gold)
    y = 48
    for text, scale in lines:
        mod._text(buf, width, 48, y, text, cream if scale < 7 else gold, scale)
        y += 8 * scale + 18
    return mod._png(width, height, mod._rows(buf, width, height))


def page(title: str, description: str, image_path: str, page_id: str, hash_route: str) -> str:
    image = f"{SITE}graphics/og/{image_path}.png"
    target = f"{SITE}#{hash_route}"
    relative = f"../index.html#{hash_route}"
    esc = html.escape
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:image" content="{esc(image)}">
  <meta property="og:url" content="{esc(SITE)}share/{esc(page_id)}.html">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">
  <meta name="twitter:image" content="{esc(image)}">
  <link rel="canonical" href="{esc(target)}">
  <meta http-equiv="refresh" content="0; url={esc(relative)}">
</head>
<body>
  <p><a href="{esc(relative)}">{esc(title)}</a></p>
  <script>location.replace("{relative}");</script>
</body>
</html>
"""


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def recap_document(data: dict, mod) -> dict:
    dated = []
    undated = []
    for game in data["games"]:
        if game.get("date"):
            dated.append(game)
        else:
            undated.append(game["id"])
    anchor = date.fromisoformat(dated[-1]["date"]) if dated else date(2026, 10, 24)
    start = week_start(anchor)
    end = start + timedelta(days=6)
    games = []
    for game in dated:
        played = date.fromisoformat(game["date"])
        if start <= played <= end:
            games.append({
                "id": game["id"],
                "date": game["date"],
                "away": game["away"],
                "home": game["home"],
                "away_name": game["teams"][game["away"]],
                "home_name": game["teams"][game["home"]],
                "away_runs": game["score"][game["away"]],
                "home_runs": game["score"][game["home"]],
                "winner": game["winner"],
                "recap": game.get("game_recap") or "",
            })
    found = mod.milestones(data)
    return {
        "id": start.isoformat(),
        "title": f"Week of {start.strftime('%B')} {start.day}, {start.year}",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "games": games,
        "undated": undated,
        "milestones": found,
    }


def recap_html(doc: dict, clubs: dict) -> str:
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        f"<title>{html.escape(doc['title'])} — Payoff Pitch</title>",
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<link rel="stylesheet" href="../css/styles.css">',
        "</head>",
        "<body>",
        '<main class="panel">',
        f"<h1>{html.escape(doc['title'])}</h1>",
        f"<p>Games dated {html.escape(doc['start'])} through {html.escape(doc['end'])}. Generated from the results feed.</p>",
    ]
    if not doc["games"]:
        parts.append("<p>No dated games fall in this week.</p>")
    for game in doc["games"]:
        winner = clubs[game["winner"]]["name"]
        parts.append(
            f"<h2>{html.escape(game['id'])}</h2>"
            f"<p>{html.escape(game['away_name'])} {game['away_runs']}, "
            f"{html.escape(game['home_name'])} {game['home_runs']}. "
            f"{html.escape(winner)} won.</p>"
        )
        if game["recap"]:
            parts.append(f"<p>{html.escape(game['recap'])}</p>")
    if doc["undated"]:
        parts.append("<h2>Undated games</h2>")
        parts.append("<p>These games are on the book and have no calendar date, so they are not counted in the week: "
                     + html.escape(", ".join(doc["undated"])) + ".</p>")
    notes = []
    for item in doc["milestones"]["nohitters"]:
        notes.append(f"{item['name']} no-hitter in {item['game']}")
    for item in doc["milestones"]["high_k"]:
        notes.append(f"{item['name']} {item['k']} strikeouts in {item['game']}")
    if notes:
        parts.append("<h2>Milestones on the book</h2><ul>")
        for note in notes:
            parts.append(f"<li>{html.escape(note)}</li>")
        parts.append("</ul>")
    parts += ['<p><a href="../index.html#/recap">Open this recap in the site</a></p>', "</main>", "</body>", "</html>", ""]
    return "\n".join(parts)


def write_share(data: dict) -> None:
    mod = _publish()
    clubs = {team["code"]: team for team in data["teams"]}
    og_games = ROOT / "graphics" / "og" / "games"
    og_series = ROOT / "graphics" / "og" / "series"
    share = ROOT / "share"
    recap_dir = ROOT / "recap"
    for folder in (og_games, og_series, share, recap_dir):
        folder.mkdir(parents=True, exist_ok=True)

    site_lines = [("PAYOFF PITCH", 6), ("TOURNAMENT 32", 8), ("DOUBLE ELIMINATION", 4)]
    (ROOT / "graphics" / "og" / "site.png").write_bytes(og_png(mod, site_lines))

    keep_share = set()
    keep_games = set()
    for game in data["games"]:
        away, home = game["away"], game["home"]
        title = f"{game['id']}: {game['teams'][away]} {game['score'][away]}, {game['teams'][home]} {game['score'][home]}"
        description = game.get("game_recap") or title
        lines = [
            ("PAYOFF PITCH", 4),
            (game["id"].replace("-", " "), 5),
            (f"{away}  {game['score'][away]}", 8),
            (f"{home}  {game['score'][home]}", 8),
            ("FINAL", 4),
        ]
        (og_games / f"{game['id']}.png").write_bytes(og_png(mod, lines))
        (share / f"{game['id']}.html").write_text(
            page(title, description, f"games/{game['id']}", game["id"], f"/game/{game['id']}"),
            encoding="utf-8",
        )
        keep_share.add(f"{game['id']}.html")
        keep_games.add(game["id"])

    keep_series = set()
    for series in data["series"]:
        if not series.get("team_a") or not series.get("team_b"):
            continue
        a, b = series["team_a"], series["team_b"]
        wins = series.get("wins") or {}
        label = "FINAL" if series["status"] == "complete" else series["status"].replace("-", " ").upper()
        title = f"{series['id']}: {clubs[a]['name']} {wins.get(a, 0)}, {clubs[b]['name']} {wins.get(b, 0)}"
        description = f"{series.get('label') or series['id']}. {label}."
        lines = [
            ("PAYOFF PITCH", 4),
            (series["id"].replace("-", " "), 5),
            (f"{a}  {wins.get(a, 0)}", 8),
            (f"{b}  {wins.get(b, 0)}", 8),
            (label[:18], 4),
        ]
        (og_series / f"{series['id']}.png").write_bytes(og_png(mod, lines))
        (share / f"{series['id']}.html").write_text(
            page(title, description, f"series/{series['id']}", series["id"], f"/series/{series['id']}"),
            encoding="utf-8",
        )
        keep_share.add(f"{series['id']}.html")
        keep_series.add(series["id"])

    for path in share.glob("*.html"):
        if path.name not in keep_share:
            path.unlink()
    for folder, keep in ((og_games, keep_games), (og_series, keep_series)):
        for path in folder.glob("*.png"):
            if path.stem not in keep:
                path.unlink()

    doc = recap_document(data, mod)
    # %-d is not portable on every Python build; format the day without a leading zero ourselves.
    start = date.fromisoformat(doc["start"])
    doc["title"] = f"Week of {start.strftime('%B')} {start.day}, {start.year}"
    (ROOT / "feed" / "recap.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    (recap_dir / f"{doc['id']}.html").write_text(recap_html(doc, clubs), encoding="utf-8")
    for path in recap_dir.glob("*.html"):
        if path.stem != doc["id"]:
            path.unlink()
    print(f"wrote share pages, og images, recap {doc['id']}")
