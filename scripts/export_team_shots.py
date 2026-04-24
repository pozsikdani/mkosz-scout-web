#!/usr/bin/env python3
"""Export per-team shot lists from mkosz_stats.sqlite to JSON.

Reads the already-generated team-matches JSON (which has home/away/opponent/score
correctly resolved via the name-alias logic), and enriches each match with
its shot list from the shots table (filtered by team_id).

Team identification uses team_id extracted from standings team_url — this is
the canonical mkosz.hu id and matches shots.team_id directly.

Shape:
{
    "team": "Vasas Akadémia",
    "team_id": 9233,
    "season": "x2526",
    "total_shots": N,
    "total_made": M,
    "matches": [
        {
            "gamecode": "hun2a_123456",
            "date": "2026-03-21",
            "opponent": "TF-BP",
            "home": true,
            "our_score": 89,
            "their_score": 70,
            "result": "W",
            "phase": "alapszakasz",
            "shots": [
                {"x": 50.0, "y": 24.0, "made": 1, "period": 1, "player": "...", "zone": "paint"},
                ...
            ]
        },
        ...
    ]
}
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT.parent / "mkosz-stats" / "mkosz_stats.sqlite"
DEFAULT_STANDINGS = REPO_ROOT / "static" / "data" / "standings" / "hun2a.json"
DEFAULT_MATCHES_DIR = REPO_ROOT / "static" / "data" / "team-matches"
DEFAULT_OUT_DIR = REPO_ROOT / "static" / "data" / "team-shots"


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


def extract_team_id(team_url: str | None) -> int | None:
    if not team_url:
        return None
    m = re.search(r"/csapat/[^/]+/[^/]+/(\d+)/", team_url)
    return int(m.group(1)) if m else None


def fetch_shots(conn: sqlite3.Connection, gamecode: str, team_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT hx, hy, is_made, period, player_name, zone, is_free_throw
        FROM shots
        WHERE gamecode = ? AND team_id = ? AND is_free_throw = 0
          AND hx IS NOT NULL AND hy IS NOT NULL
        ORDER BY period, id
        """,
        (gamecode, team_id),
    ).fetchall()
    return [
        {
            "x": round(hx, 1),
            "y": round(hy, 1),
            "made": int(made),
            "period": int(period),
            "player": player,
            "zone": zone,
        }
        for (hx, hy, made, period, player, zone, _is_ft) in rows
    ]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--standings", default=str(DEFAULT_STANDINGS))
    p.add_argument("--matches-dir", default=str(DEFAULT_MATCHES_DIR))
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--season", default="x2526")
    args = p.parse_args()

    standings = json.loads(Path(args.standings).read_text(encoding="utf-8"))
    matches_dir = Path(args.matches_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(args.db)
    written = 0
    for team in standings["teams"]:
        team_name = team["team"]
        team_id = extract_team_id(team.get("team_url"))
        if not team_id:
            print(f"  ⚠ {team_name}: no team_id, skipping", file=sys.stderr)
            continue

        slug = slugify(team_name)
        matches_path = matches_dir / f"{slug}.json"
        if not matches_path.exists():
            print(f"  ⚠ {team_name}: matches JSON missing ({matches_path})", file=sys.stderr)
            continue
        matches_data = json.loads(matches_path.read_text(encoding="utf-8"))

        enriched: list[dict] = []
        total_shots = total_made = 0
        for m in matches_data["matches"]:
            # Only include matches that have been played (result not None).
            # Unplayed future matches are excluded entirely.
            if m["result"] is None:
                continue
            shots = fetch_shots(conn, m["gamecode"], team_id)
            total_shots += len(shots)
            total_made += sum(s["made"] for s in shots)
            enriched.append({
                "gamecode": m["gamecode"],
                "phase": m["phase"],
                "date": m["date"],
                "opponent": m["opponent"],
                "home": m["home"],
                "our_score": m["our_score"],
                "their_score": m["their_score"],
                "result": m["result"],
                "has_shotchart": len(shots) > 0,
                "shots": shots,
            })

        payload = {
            "team": team_name,
            "team_id": team_id,
            "season": args.season,
            "total_shots": total_shots,
            "total_made": total_made,
            "matches": enriched,
        }
        out_path = out_dir / f"{slug}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
        written += 1
        fg_pct = (100.0 * total_made / total_shots) if total_shots else 0
        print(f"  {team_name:<40} {len(enriched):>2} meccs  {total_shots:>5} lövés  {total_made:>4} bement  FG% {fg_pct:5.1f}")

    conn.close()
    print(f"\nÖsszesen: {written} fájl → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
