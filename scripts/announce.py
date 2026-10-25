#!/usr/bin/env python3
"""Post new final scores after a deploy, only when the secrets are set.

Discord uses DISCORD_WEBHOOK_URL. X uses X_API_KEY, X_API_SECRET,
X_ACCESS_TOKEN, and X_ACCESS_TOKEN_SECRET. A missing secret skips that
destination. Nothing is posted when there is no new final.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "tournament_results.json"
SITE = "https://dvdjoe-sudo.github.io/Payoff-pitch-tournament-32"


def configured(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def load_at(rev: str) -> dict | None:
    if not rev or set(rev) <= {"0"}:
        return None
    try:
        text = subprocess.check_output(
            ["git", "show", f"{rev}:tournament_results.json"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None
    return json.loads(text)


def new_finals(before: dict | None, after: dict) -> tuple[list[dict], list[dict]]:
    old_games = {game["id"] for game in (before or {}).get("games", [])}
    games = [game for game in after["games"] if game["id"] not in old_games]
    old_series = {item["id"]: item for item in (before or {}).get("series", [])}
    series = []
    for item in after["series"]:
        if item.get("status") != "complete" or not item.get("winner"):
            continue
        previous = old_series.get(item["id"])
        if previous is None or previous.get("status") != "complete":
            if item.get("team_a") and item.get("team_b"):
                series.append(item)
    return games, series


def game_text(game: dict) -> tuple[str, str, Path]:
    away, home = game["away"], game["home"]
    text = (
        f"Final: {game['teams'][away]} {game['score'][away]}, "
        f"{game['teams'][home]} {game['score'][home]} ({game['id']}). "
        f"{SITE}/share/{game['id']}.html"
    )
    image = ROOT / "graphics" / "og" / "games" / f"{game['id']}.png"
    if not image.is_file():
        image = ROOT / "graphics" / "games" / f"{game['id']}.png"
    return text, f"{SITE}/graphics/og/games/{game['id']}.png", image


def series_text(series: dict, clubs: dict[str, dict]) -> tuple[str, str, Path]:
    winner = clubs[series["winner"]]["name"]
    loser = clubs[series["loser"]]["name"]
    wins = series.get("wins") or {}
    text = (
        f"Series final: {winner} beat {loser} "
        f"{wins.get(series['winner'], 0)}-{wins.get(series['loser'], 0)} ({series['id']}). "
        f"{SITE}/share/{series['id']}.html"
    )
    image = ROOT / "graphics" / "og" / "series" / f"{series['id']}.png"
    if not image.is_file():
        image = ROOT / "graphics" / "series" / f"{series['id']}.png"
    return text, f"{SITE}/graphics/og/series/{series['id']}.png", image


def post_discord(webhook: str, text: str, image: Path) -> None:
    boundary = "----payoffpitch" + secrets.token_hex(8)
    payload = json.dumps({"content": text}).encode()
    png = image.read_bytes() if image.is_file() else b""
    body = []
    body.append(f"--{boundary}\r\n".encode())
    body.append(b'Content-Disposition: form-data; name="payload_json"\r\n\r\n')
    body.append(payload)
    body.append(b"\r\n")
    if png:
        body.append(f"--{boundary}\r\n".encode())
        body.append(f'Content-Disposition: form-data; name="files[0]"; filename="{image.name}"\r\n'.encode())
        body.append(b"Content-Type: image/png\r\n\r\n")
        body.append(png)
        body.append(b"\r\n")
    body.append(f"--{boundary}--\r\n".encode())
    request = urllib.request.Request(
        webhook,
        data=b"".join(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "payoff-pitch-announce"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


def oauth_header(method: str, url: str, keys: dict[str, str]) -> str:
    parsed = urllib.parse.urlparse(url)
    oauth = {
        "oauth_consumer_key": keys["consumer"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": keys["token"],
        "oauth_version": "1.0",
    }
    collected = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    collected.update(oauth)
    encoded = "&".join(
        f"{urllib.parse.quote(key, safe='')}={urllib.parse.quote(collected[key], safe='')}"
        for key in sorted(collected)
    )
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    base = "&".join([
        method.upper(),
        urllib.parse.quote(base_url, safe=""),
        urllib.parse.quote(encoded, safe=""),
    ])
    signing = "&".join([
        urllib.parse.quote(keys["consumer_secret"], safe=""),
        urllib.parse.quote(keys["token_secret"], safe=""),
    ])
    digest = hmac.new(signing.encode(), base.encode(), hashlib.sha1).digest()
    oauth["oauth_signature"] = base64.b64encode(digest).decode()
    return "OAuth " + ", ".join(
        f'{urllib.parse.quote(key, safe="")}="{urllib.parse.quote(oauth[key], safe="")}"'
        for key in sorted(oauth)
    )


def x_keys() -> dict[str, str] | None:
    names = {
        "consumer": "X_API_KEY",
        "consumer_secret": "X_API_SECRET",
        "token": "X_ACCESS_TOKEN",
        "token_secret": "X_ACCESS_TOKEN_SECRET",
    }
    found = {key: configured(env) for key, env in names.items()}
    if not all(found.values()):
        return None
    return found


def post_x(keys: dict[str, str], text: str, image: Path) -> None:
    media_ids = []
    if image.is_file():
        upload = "https://upload.twitter.com/1.1/media/upload.json"
        boundary = "----payoffpitch" + secrets.token_hex(8)
        png = image.read_bytes()
        chunks = [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="media"\r\n',
            b"Content-Type: application/octet-stream\r\n\r\n",
            png,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
        request = urllib.request.Request(
            upload,
            data=b"".join(chunks),
            headers={
                "Authorization": oauth_header("POST", upload, keys),
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "User-Agent": "payoff-pitch-announce",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
        media_id = payload.get("media_id_string") or str(payload.get("media_id") or "")
        if media_id:
            media_ids.append(media_id)
    tweet = "https://api.twitter.com/2/tweets"
    body = {"text": text[:280]}
    if media_ids:
        body["media"] = {"media_ids": media_ids}
    request = urllib.request.Request(
        tweet,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": oauth_header("POST", tweet, keys),
            "Content-Type": "application/json",
            "User-Agent": "payoff-pitch-announce",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


def main() -> int:
    before_rev = configured("GITHUB_BEFORE") or configured("BEFORE")
    after = json.loads(RESULTS.read_text(encoding="utf-8"))
    before = load_at(before_rev)
    if before is None and before_rev:
        print("announce: previous results were not available; skipping")
        return 0
    if before is None:
        print("announce: no previous commit; skipping")
        return 0
    games, series = new_finals(before, after)
    if not games and not series:
        print("announce: no new final")
        return 0
    clubs = {team["code"]: team for team in after["teams"]}
    posts = [game_text(game) for game in games] + [series_text(item, clubs) for item in series]
    webhook = configured("DISCORD_WEBHOOK_URL")
    keys = x_keys()
    if not webhook and not keys:
        print("announce skipped; secrets unset")
        return 0
    for text, _url, image in posts:
        if webhook:
            post_discord(webhook, text, image)
            print("posted to Discord")
        if keys:
            post_x(keys, text, image)
            print("posted to X")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
