#!/usr/bin/env python3
"""Scrape MKOSZ team-roster pages → JSON with name/jersey/position/height/photo URL.

For each team in the standings, fetches `team_url` (e.g.
`https://mkosz.hu/csapat/x2526/hun2a/40067/phoenix-mt-fot`), parses the player
table and extracts photo URL from the inline CSS background-image.

Output: static/data/rosters/hun2a.json
{
    "season": "x2526",
    "comp": "hun2a",
    "scraped_at": "...",
    "teams": {
        "vasas-akademia": {
            "team": "Vasas Akadémia",
            "team_url": "...",
            "players": [
                {"name": "Fekete Viktor Norbert", "jersey": 7,
                 "position": "1-2", "height_cm": 186, "birth_year": 2005,
                 "photo_url": "https://...", "photo_filename": "vasas-akademia-fekete-viktor-norbert.jpg"}
            ]
        }
    }
}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STANDINGS = REPO_ROOT / "static" / "data" / "standings" / "hun2a.json"
DEFAULT_OUT_DIR = REPO_ROOT / "static" / "data" / "rosters"


def slugify(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    out: list[str] = []
    prev_dash = False
    for c in stripped.lower():
        if c.isalnum():
            out.append(c)
            prev_dash = False
        elif not prev_dash and out:
            out.append("-")
            prev_dash = True
    return "".join(out).rstrip("-")


def parse_int(s: str) -> int | None:
    s = (s or "").strip()
    m = re.search(r"\d+", s)
    return int(m.group(0)) if m else None


def scrape_team_roster(team_url: str) -> list[dict]:
    """Parse player table at given URL → list of player dicts."""
    resp = requests.get(team_url, timeout=15)
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    players: list[dict] = []
    for row in soup.select("table tr")[1:]:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
        jersey = parse_int(cols[0].get_text(strip=True))
        link = cols[1].find("a")
        name = (link.get("title", "").strip() if link else cols[1].get_text(strip=True)).strip()
        if not name:
            continue
        birth = parse_int(cols[2].get_text(strip=True))
        pos = cols[3].get_text(strip=True) or None
        height = parse_int(cols[4].get_text(strip=True))

        pic_div = cols[1].find("div", class_="team-players-pic")
        pic_url = ""
        if pic_div:
            style = pic_div.get("style", "") or ""
            m = re.search(r"url\(([^)]+)\)", style)
            if m:
                pic_url = m.group(1).strip().strip("'\"")
                if "placeholder" in pic_url.lower():
                    pic_url = ""

        players.append({
            "name": name,
            "jersey": jersey,
            "position": pos,
            "height_cm": height,
            "birth_year": birth,
            "photo_url": pic_url or None,
        })
    return players


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--standings", default=str(DEFAULT_STANDINGS))
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--comp", default="hun2a")
    args = p.parse_args()

    standings = json.loads(Path(args.standings).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    teams_out: dict[str, dict] = {}
    total_players = 0
    total_photos = 0
    for t in standings["teams"]:
        team_name = t["team"]
        team_url = t.get("team_url")
        if not team_url:
            print(f"  WARN: no team_url for {team_name}", file=sys.stderr)
            continue
        team_slug = slugify(team_name)
        try:
            players = scrape_team_roster(team_url)
        except Exception as e:
            print(f"  ERROR {team_name}: {e}", file=sys.stderr)
            continue

        for pl in players:
            pl["photo_filename"] = (
                f"{team_slug}-{slugify(pl['name'])}.jpg" if pl.get("photo_url") else None
            )
            if pl.get("photo_url"):
                total_photos += 1
        total_players += len(players)
        teams_out[team_slug] = {
            "team": team_name,
            "team_url": team_url,
            "players": players,
        }
        with_pic = sum(1 for pl in players if pl.get("photo_url"))
        print(f"  {team_name:<40} → {len(players):>2} játékos ({with_pic} fotóval)")

    payload = {
        "season": standings.get("season", "x2526"),
        "comp": args.comp,
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "team_count": len(teams_out),
        "player_count": total_players,
        "photo_count": total_photos,
        "teams": teams_out,
    }
    out_path = out_dir / f"{args.comp}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nÖsszesen: {len(teams_out)} csapat, {total_players} játékos ({total_photos} fotóval) → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
