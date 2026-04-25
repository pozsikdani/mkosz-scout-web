#!/usr/bin/env python3
"""Export per-team, per-game possession-breakdown raw counts.

Mirrors §1.5 logic from mockup_s1s2.py: event-by-event possession outcome
counting, with the OREB rule (a missed FG / FT trip followed by an OREB
does NOT count as a failed possession). Pace components (FGA/FTA/OREB/TOV)
also recorded per game so the JS UI can recompute /g aggregates correctly
when the user filters to an arbitrary subset of games.

Output: static/data/team-possessions/{slug}.json
{
    "team": "Vasas Akadémia",
    "season": "x2526",
    "match_count": 28,
    "matches": [
        {
            "gamecode": "hun2a_123471",
            "phase": "alapszakasz",
            "date": "2025-09-21",
            "opponent": "...",
            "home": true, "result": "W",
            "our_score": 89, "their_score": 70,
            "has_pbp": true,
            "counts": {
                // Successful possessions (events that ended a possession positively)
                "close_m": 19, "mid_m": 2, "three_m": 8, "dunk_m": 1, "ft": 10,
                // Failed possessions (after OREB filter)
                "close_x": 10, "mid_x": 4, "three_x": 13, "dunk_x": 0, "tov": 14,
                // Pace components (raw — for FGA + 0.44*FTA + TOV - OREB)
                "fga": 60, "fta": 22, "oreb": 8, "tov_total": 14
            }
        }
    ]
}
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
DEFAULT_OUT_DIR = REPO_ROOT / "static" / "data" / "team-possessions"

COMPS = ("hun2a", "hun2a_ply", "hun2a_plya")
PHASE_MAP = {
    "hun2a": "alapszakasz",
    "hun2a_ply": "rajatszas_felso",
    "hun2a_plya": "rajatszas_also",
}

TEAM_ALIASES: dict[str, list[str]] = {
    "EBH-Salgótarján": ["Salgótarjáni KSE"],
}

FT_TYPES = {"FT_MADE", "FT_MISS"}
FGA_TYPES = {
    "CLOSE_MADE", "CLOSE_MISS", "MID_MADE", "MID_MISS",
    "THREE_MADE", "THREE_MISS", "DUNK_MADE", "DUNK_MISS",
}
MISS_TYPES = {"CLOSE_MISS", "MID_MISS", "THREE_MISS", "DUNK_MISS"}


def norm_full(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def team_matches(canonical_name: str, db_name: str, aliases: list[str]) -> bool:
    db_full = norm_full(db_name)
    if len(db_full) < 5:
        return False
    for cand in [canonical_name, *aliases]:
        cand_full = norm_full(cand)
        if cand_full[:12] in db_full or db_full in cand_full:
            return True
    return False


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


def compute_game_counts(events: list[str]) -> dict[str, int]:
    """Apply the §1.5 event-by-event possession-outcome rules to one game."""
    c = {
        "close_m": 0, "mid_m": 0, "three_m": 0, "dunk_m": 0, "ft": 0,
        "close_x": 0, "mid_x": 0, "three_x": 0, "dunk_x": 0, "tov": 0,
        "fga": 0, "fta": 0, "oreb": 0, "tov_total": 0,
    }
    # Pace components first (independent of OREB filter)
    for ev in events:
        if ev in FGA_TYPES:
            c["fga"] += 1
        elif ev in FT_TYPES:
            c["fta"] += 1
        elif ev == "OREB":
            c["oreb"] += 1
        elif ev == "TOV":
            c["tov_total"] += 1
    # Event-by-event possession counting (with OREB filter)
    i = 0
    n = len(events)
    while i < n:
        et = events[i]
        if et == "CLOSE_MADE":
            c["close_m"] += 1
        elif et == "MID_MADE":
            c["mid_m"] += 1
        elif et == "THREE_MADE":
            c["three_m"] += 1
        elif et == "DUNK_MADE":
            c["dunk_m"] += 1
        elif et == "TOV":
            c["tov"] += 1
        elif et in MISS_TYPES:
            if not (i + 1 < n and events[i + 1] == "OREB"):
                if et == "CLOSE_MISS":
                    c["close_x"] += 1
                elif et == "MID_MISS":
                    c["mid_x"] += 1
                elif et == "THREE_MISS":
                    c["three_x"] += 1
                elif et == "DUNK_MISS":
                    c["dunk_x"] += 1
        elif et in FT_TYPES:
            # Skip to end of FT trip; count one possession unless followed by OREB
            while i < n and events[i] in FT_TYPES:
                i += 1
            i -= 1
            if not (i + 1 < n and events[i + 1] == "OREB"):
                c["ft"] += 1
        i += 1
    return c


def fetch_events_for_team_game(
    conn: sqlite3.Connection, gamecode: str, team_side: str
) -> list[str]:
    rows = conn.execute(
        "SELECT event_type FROM pbp_events WHERE gamecode=? AND team=? ORDER BY event_seq",
        (gamecode, team_side),
    ).fetchall()
    return [r[0] for r in rows]


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
        aliases = TEAM_ALIASES.get(team, [])
        match_rows = conn.execute(
            f"""
            SELECT gamecode, comp_code, match_date, team_a_name, team_b_name,
                   score_a, score_b, has_pbp
            FROM matches
            WHERE season = ? AND comp_code IN ({",".join("?" for _ in COMPS)})
            ORDER BY match_date, gamecode
            """,
            (args.season, *COMPS),
        ).fetchall()

        out_matches: list[dict] = []
        for gc, comp, mdate, ta, tb, sa, sb, has_pbp in match_rows:
            is_a = team_matches(team, ta, aliases)
            is_b = team_matches(team, tb, aliases)
            if not (is_a or is_b):
                continue
            if not (sa and sb):
                continue
            team_side = "A" if is_a else "B"
            home = is_a
            opp = tb if is_a else ta
            our = sa if is_a else sb
            their = sb if is_a else sa
            result = "W" if our > their else ("L" if our < their else "D")

            counts = None
            if has_pbp:
                events = fetch_events_for_team_game(conn, gc, team_side)
                if events:
                    counts = compute_game_counts(events)

            out_matches.append({
                "gamecode": gc,
                "comp_code": comp,
                "phase": PHASE_MAP.get(comp, comp),
                "date": mdate,
                "opponent": opp,
                "home": home,
                "result": result,
                "our_score": our,
                "their_score": their,
                "has_pbp": bool(has_pbp and counts is not None),
                "counts": counts,
            })

        out_matches.sort(key=lambda m: (m["date"] or "", m["gamecode"]))

        payload = {
            "team": team,
            "season": args.season,
            "match_count": len(out_matches),
            "matches": out_matches,
        }
        out_path = out_dir / f"{slugify(team)}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written += 1
        with_pbp = sum(1 for m in out_matches if m["has_pbp"])
        print(f"  {team:<40} → {len(out_matches)} meccs ({with_pbp} PBP-vel)")

    conn.close()
    print(f"\nÖsszesen: {written} fájl → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
