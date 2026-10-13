#!/usr/bin/env python3
"""Guard: every exported stat for a season must come only from that season.

Fails (exit 1) if any team-level JSON references a gamecode from another
season, or if a player / league-comparison game count exceeds the number of
games the team actually played in this season. Run after the exports, before
committing, so a mixed-season bug never reaches the live site.
"""
from __future__ import annotations

import argparse
import glob
import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GAME_KINDS = ("team-matches", "team-shots", "team-possessions", "team-lineups", "team-lineup-nrtg")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--season", required=True)
    p.add_argument("--comps", nargs="+", required=True)
    args = p.parse_args()

    season_of = dict(sqlite3.connect(args.db).execute("SELECT gamecode, season FROM matches"))
    data = REPO_ROOT / "static" / "data" / args.season
    errors: list[str] = []

    for comp in args.comps:
        for kind in GAME_KINDS:
            for f in glob.glob(str(data / kind / comp / "*.json")):
                for m in json.load(open(f, encoding="utf-8")).get("matches", []):
                    s = season_of.get(m["gamecode"])
                    if s != args.season:
                        errors.append(f"{kind}/{comp}/{Path(f).name}: {m['gamecode']} szezonja {s}")

        played: dict[str, int] = {}
        for f in glob.glob(str(data / "team-matches" / comp / "*.json")):
            d = json.load(open(f, encoding="utf-8"))
            played[Path(f).stem] = sum(1 for m in d["matches"] if m.get("result"))
        max_played = max(played.values(), default=0)

        for f in glob.glob(str(data / "team-players" / comp / "*.json")):
            limit = played.get(Path(f).stem, max_played)
            for pl in json.load(open(f, encoding="utf-8"))["players"]:
                if pl["gp"] > limit:
                    errors.append(f"team-players/{comp}/{Path(f).name}: {pl['name']} gp={pl['gp']} > {limit} lejátszott meccs")

        lc = data / "league-comparison" / f"{comp}.json"
        if lc.exists():
            for t in json.load(open(lc, encoding="utf-8"))["teams"]:
                if t["gp"] > max_played:
                    errors.append(f"league-comparison/{comp}: {t['team']} gp={t['gp']} > {max_played}")

    if errors:
        print(f"SZEZON-KEVEREDÉS ({args.season}): {len(errors)} hiba", file=sys.stderr)
        for e in errors[:30]:
            print("  " + e, file=sys.stderr)
        return 1
    print(f"Szezon-izoláció OK ({args.season}: {', '.join(args.comps)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
