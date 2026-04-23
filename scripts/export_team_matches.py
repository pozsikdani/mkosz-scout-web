#!/usr/bin/env python3
"""Export per-team match lists from mkosz_stats.sqlite to JSON.

For each team listed in the standings JSON, writes one file to
`static/data/team-matches/{slug}.json` with ALL matches (alapszakasz + playoff),
date-sorted ascending. The frontend slices last N.

Team name matching: the standings has canonical form (Title Case, e.g. "Vasas Akadémia"),
but the DB has inconsistent casing. We match case-insensitively using NFKD-normalized
prefix (first 12 chars) to collapse "VASAS AKADÉMIA" and "Vasas Akadémia".
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unicodedata
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT.parent / "mkosz-stats" / "mkosz_stats.sqlite"
DEFAULT_STANDINGS = REPO_ROOT / "static" / "data" / "standings" / "hun2a.json"
DEFAULT_OUT_DIR = REPO_ROOT / "static" / "data" / "team-matches"

PLAYOFF_BRACKETS = {
    "hun2a": "alapszakasz",
    "hun2a_ply": "rajatszas_felso",
    "hun2a_plya": "rajatszas_also",
}


def norm_key(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return stripped.lower().strip()[:12]


def slugify(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    out = []
    prev_dash = False
    for c in stripped.lower():
        if c.isalnum():
            out.append(c)
            prev_dash = False
        elif not prev_dash and out:
            out.append("-")
            prev_dash = True
    return "".join(out).rstrip("-")


def fetch_matches_for_team(conn: sqlite3.Connection, team_name: str, season: str) -> list[dict]:
    key = norm_key(team_name)
    rows = conn.execute(
        """
        SELECT gamecode, comp_code, season, round_name, match_date, match_time,
               team_a_name, team_b_name, score_a, score_b, quarter_scores,
               has_scoresheet, has_pbp, has_shotchart
        FROM matches
        WHERE season = ?
          AND comp_code IN (%s)
        """
        % ",".join("?" for _ in PLAYOFF_BRACKETS),
        (season, *PLAYOFF_BRACKETS.keys()),
    ).fetchall()

    matches = []
    for row in rows:
        (gamecode, comp_code, season_, round_name, match_date, match_time,
         team_a, team_b, score_a, score_b, quarter_scores,
         has_ss, has_pbp, has_sc) = row

        a_key = norm_key(team_a)
        b_key = norm_key(team_b)
        if not (a_key.startswith(key) or b_key.startswith(key)):
            continue

        is_home = a_key.startswith(key)
        opp = team_b if is_home else team_a
        our_score = score_a if is_home else score_b
        their_score = score_b if is_home else score_a
        has_result = our_score is not None and their_score is not None and (our_score or their_score)

        result = None
        if has_result:
            result = "W" if our_score > their_score else ("L" if our_score < their_score else "D")

        matches.append({
            "gamecode": gamecode,
            "comp_code": comp_code,
            "phase": PLAYOFF_BRACKETS.get(comp_code, comp_code),
            "round": round_name,
            "date": match_date,
            "time": match_time,
            "home": is_home,
            "opponent": opp,
            "our_score": our_score if has_result else None,
            "their_score": their_score if has_result else None,
            "result": result,
            "has_scoresheet": bool(has_ss),
            "has_pbp": bool(has_pbp),
        })

    matches.sort(key=lambda m: (m["date"] or "", m["gamecode"]))
    return matches


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--standings", default=str(DEFAULT_STANDINGS))
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--season", default="x2526")
    args = p.parse_args()

    standings_path = Path(args.standings)
    if not standings_path.exists():
        print(f"ERROR: standings not found: {standings_path}", file=sys.stderr)
        return 1

    standings = json.loads(standings_path.read_text(encoding="utf-8"))
    teams = [t["team"] for t in standings["teams"]]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(args.db)
    written = 0
    for team in teams:
        matches = fetch_matches_for_team(conn, team, args.season)
        payload = {
            "team": team,
            "season": args.season,
            "count": len(matches),
            "matches": matches,
        }
        out_path = out_dir / f"{slugify(team)}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written += 1
        print(f"  {team:<40} → {len(matches)} meccs")

    conn.close()
    print(f"\nÖsszesen: {written} fájl → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
