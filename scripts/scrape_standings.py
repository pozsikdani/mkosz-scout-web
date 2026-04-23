#!/usr/bin/env python3
"""Scrape the MKOSZ standings table for a given competition and season.

Output: static/data/standings/{comp}.json — consumed by the SvelteKit app.
Defaults: season=x2526, comp=hun2a (NB1 B Piros).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


COMP_DISPLAY_NAMES = {
    "hun2a": "NB1 B Piros",
    "hun2b": "NB1 B Zöld",
    "hun_univn": "MEFOB Férfi Nyugat",
    "hun_univk": "MEFOB Férfi Kelet",
}


def scrape_standings(season: str, comp: str) -> list[dict]:
    url = f"https://mkosz.hu/bajnoksag/{season}/{comp}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.content.decode("utf-8", errors="replace"), "html.parser")

    teams: list[dict] = []
    for tbl in soup.find_all("table"):
        rows = tbl.find_all("tr")
        if len(rows) < 10:
            continue
        header_cells = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
        if not any("Csapat" in h or "%" in h for h in header_cells):
            continue
        for row in rows[1:]:
            tds = row.find_all("td")
            cells = [td.get_text(strip=True) for td in tds]
            if len(cells) < 10:
                continue
            rank = cells[0].rstrip(".")
            team_name = cells[2]
            link = tds[2].find("a") if len(tds) > 2 else None
            href = link.get("href") if link else None
            if href and href.startswith("/"):
                team_url = "https://mkosz.hu" + href
            elif href and href.startswith("http"):
                team_url = href
            else:
                team_url = None
            gp = int(cells[3]) if cells[3].isdigit() else 0
            wins = int(cells[6]) if cells[6].isdigit() else 0
            losses = int(cells[7]) if cells[7].isdigit() else 0
            scored = int(cells[8]) if cells[8].isdigit() else 0
            allowed = int(cells[9]) if cells[9].isdigit() else 0
            streak_raw = cells[10] if len(cells) > 10 else ""
            streak = streak_raw.replace("GY", "W").replace("V", "L")
            home = cells[11] if len(cells) > 11 else ""
            away = cells[12] if len(cells) > 12 else ""
            last5 = cells[13] if len(cells) > 13 else ""
            teams.append({
                "rank": int(rank) if rank.isdigit() else rank,
                "team": team_name,
                "gp": gp,
                "w": wins,
                "l": losses,
                "scored": scored,
                "allowed": allowed,
                "streak": streak,
                "home": home,
                "away": away,
                "last5": last5,
                "team_url": team_url,
            })
        break
    return teams


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--season", default="x2526")
    p.add_argument("--comp", default="hun2a")
    p.add_argument("--out", default=None, help="output path (default: static/data/standings/{comp}.json)")
    args = p.parse_args()

    teams = scrape_standings(args.season, args.comp)
    if not teams:
        print(f"ERROR: no teams scraped from mkosz.hu/bajnoksag/{args.season}/{args.comp}", file=sys.stderr)
        return 1

    payload = {
        "season": args.season,
        "comp": args.comp,
        "display_name": COMP_DISPLAY_NAMES.get(args.comp, args.comp),
        "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_url": f"https://mkosz.hu/bajnoksag/{args.season}/{args.comp}",
        "teams": teams,
    }

    if args.out:
        out_path = Path(args.out)
    else:
        repo_root = Path(__file__).resolve().parent.parent
        out_path = repo_root / "static" / "data" / "standings" / f"{args.comp}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(teams)} teams → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
