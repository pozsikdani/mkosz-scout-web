#!/usr/bin/env python3
"""Export per-team, per-player shot lists for the mini heatmap on player cards.

Reads shots for each team (hun2a + playoffs), groups them by canonical player
name (matching team-players/{slug}.json so the frontend can join on `name`),
and writes one file per team plus a league baseline FG% per shotchart zone.

Output: static/data/team-player-shots/{slug}.json
{
  "team": "...",
  "team_id": 9233,
  "season": "x2526",
  "players": {
    "Nagy Botond Ágoston": {"shots": [{"x": 43.0, "y": 16.0, "made": 0}, ...]},
    ...
  },
  "league_baselines": {
    "ra":            {"made": 4823, "att": 7321, "fg_pct": 0.659},
    "paint":         {...},
    ...
  }
}

Zone classification + league baselines are computed in Python here using the
exact same geometry as src/lib/components/ShotchartZones.svelte (Y_SCALE=0.77,
elliptical 3pt arc with rx=44/ry≈51.76, etc.) so frontend and export agree.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib.name_key import player_dedup_key  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT.parent / "mkosz-stats" / "mkosz_stats.sqlite"
DEFAULT_STANDINGS = REPO_ROOT / "static" / "data" / "standings" / "hun2a.json"
DEFAULT_PLAYERS_DIR = REPO_ROOT / "static" / "data" / "team-players"
DEFAULT_OUT_DIR = REPO_ROOT / "static" / "data" / "team-player-shots"

COMPS = ("hun2a", "hun2a_ply", "hun2a_plya")

# Geometry — must match src/lib/components/ShotchartZones.svelte exactly
Y_SCALE = 0.77
PAINT_W = 32
PAINT_H = 24
PAINT_LEFT = 50 - PAINT_W / 2   # 34
PAINT_RIGHT = 50 + PAINT_W / 2  # 66
THREE_R = 44
THREE_RY = THREE_R / Y_SCALE     # ≈51.76
CORNER_HY = 12
BASKET_HY = 3
RA_R = 9
RA_RY_HY = RA_R / Y_SCALE        # ≈11.69
WING_SPLIT_ANGLE = 25

ZONE_KEYS = (
    "ra", "paint",
    "short_corner_l", "short_corner_r",
    "mid_wing_l", "mid_wing_r", "top_key",
    "corner3_l", "wing3_l", "above_break_3", "wing3_r", "corner3_r",
)


def angle_from_basket(hx: float, hy: float) -> float:
    # W cancels in atan2 ratio, so angle is W-independent.
    dx = hx - 50
    dy_logical = max((hy - BASKET_HY) * Y_SCALE, 0.001)
    return math.degrees(math.atan2(dx, dy_logical))


def elliptical_frac(hx: float, hy: float, rhx: float, rhy: float) -> float:
    ex = (hx - 50) / rhx
    ey = (hy - BASKET_HY) / rhy
    return ex * ex + ey * ey


def classify_zone(hx: float, hy: float) -> str:
    ang = angle_from_basket(hx, hy)
    inside_three = elliptical_frac(hx, hy, THREE_R, THREE_RY) <= 1
    in_corner_rect = hy <= CORNER_HY and (hx <= 6 or hx >= 94)
    outside3 = (not inside_three) or in_corner_rect
    if outside3:
        if in_corner_rect and hx <= 6:
            return "corner3_l"
        if in_corner_rect and hx >= 94:
            return "corner3_r"
        if ang < -WING_SPLIT_ANGLE:
            return "wing3_l"
        if ang > WING_SPLIT_ANGLE:
            return "wing3_r"
        return "above_break_3"
    if elliptical_frac(hx, hy, RA_R, RA_RY_HY) <= 1:
        return "ra"
    if PAINT_LEFT <= hx <= PAINT_RIGHT and hy <= PAINT_H:
        return "paint"
    if hy <= CORNER_HY and 6 < hx < PAINT_LEFT:
        return "short_corner_l"
    if hy <= CORNER_HY and PAINT_RIGHT < hx < 94:
        return "short_corner_r"
    if PAINT_LEFT <= hx <= PAINT_RIGHT:
        return "top_key"
    if hx < PAINT_LEFT:
        return "mid_wing_l"
    return "mid_wing_r"


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


def extract_team_id(team_url: str | None) -> int | None:
    if not team_url:
        return None
    m = re.search(r"/csapat/[^/]+/[^/]+/(\d+)/", team_url)
    return int(m.group(1)) if m else None


def load_player_canonical(players_path: Path) -> dict[str, str]:
    """{dedup_key: canonical_name} from team-players/{slug}.json."""
    if not players_path.exists():
        return {}
    data = json.loads(players_path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for p in data.get("players", []):
        out[player_dedup_key(p["name"])] = p["name"]
    return out


def fetch_team_shots(conn: sqlite3.Connection, team_id: int, season: str) -> list[tuple]:
    rows = conn.execute(
        f"""
        SELECT s.hx, s.hy, s.is_made, s.player_name
        FROM shots s
        JOIN matches m USING(gamecode)
        WHERE s.team_id = ? AND m.season = ?
          AND m.comp_code IN ({",".join("?" for _ in COMPS)})
          AND s.is_free_throw = 0
          AND s.hx IS NOT NULL AND s.hy IS NOT NULL
          AND s.player_name IS NOT NULL AND s.player_name != ''
        """,
        (team_id, season, *COMPS),
    ).fetchall()
    return rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--standings", default=str(DEFAULT_STANDINGS))
    p.add_argument("--players-dir", default=str(DEFAULT_PLAYERS_DIR))
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--season", default="x2526")
    args = p.parse_args()

    standings = json.loads(Path(args.standings).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    players_dir = Path(args.players_dir)

    conn = sqlite3.connect(args.db)

    league_zone = {z: {"made": 0, "att": 0} for z in ZONE_KEYS}
    written = 0

    for team in standings["teams"]:
        team_name = team["team"]
        team_id = extract_team_id(team.get("team_url"))
        if not team_id:
            print(f"  ⚠ {team_name}: no team_id, skipping", file=sys.stderr)
            continue

        slug = slugify(team_name)
        canonical = load_player_canonical(players_dir / f"{slug}.json")

        rows = fetch_team_shots(conn, team_id, args.season)

        per_player: dict[str, list[dict]] = defaultdict(list)
        unmatched: set[str] = set()
        for hx, hy, made, name in rows:
            zone = classify_zone(float(hx), float(hy))
            league_zone[zone]["att"] += 1
            if int(made) == 1:
                league_zone[zone]["made"] += 1
            key = player_dedup_key(name)
            display = canonical.get(key)
            if not display:
                # Player has no scoresheet rows on this team — skip rather than
                # invent an unjoinable entry.
                unmatched.add(name)
                continue
            per_player[display].append({
                "x": round(float(hx), 1),
                "y": round(float(hy), 1),
                "made": int(made),
            })

        payload_players = {n: {"shots": shots} for n, shots in per_player.items()}
        # Skip writing teams with zero shots (no PBP yet)
        if not payload_players:
            print(f"  – {team_name:<40} (no shots)")
            continue

        out_path = out_dir / f"{slug}.json"
        # Baselines written in second pass below; placeholder for now.
        out_path.write_text(
            json.dumps({
                "team": team_name,
                "team_id": team_id,
                "season": args.season,
                "players": payload_players,
                "_pending_baselines": True,
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written += 1
        total = sum(len(v["shots"]) for v in payload_players.values())
        unm = f"  ({len(unmatched)} unmatched)" if unmatched else ""
        print(f"  {team_name:<40} {len(payload_players):>2} játékos  {total:>5} lövés{unm}")

    # Compute league baselines and patch every file
    baselines = {
        z: {
            "made": league_zone[z]["made"],
            "att": league_zone[z]["att"],
            "fg_pct": round(league_zone[z]["made"] / league_zone[z]["att"], 4)
            if league_zone[z]["att"] > 0 else None,
        }
        for z in ZONE_KEYS
    }

    for f in out_dir.glob("*.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        data.pop("_pending_baselines", None)
        data["league_baselines"] = baselines
        f.write_text(json.dumps(data, ensure_ascii=False) + "\n", encoding="utf-8")

    conn.close()
    print(f"\nÖsszesen: {written} fájl → {out_dir}")
    print(f"Liga baseline (FG% per zóna):")
    for z in ZONE_KEYS:
        b = baselines[z]
        pct = f"{100*b['fg_pct']:.1f}%" if b["fg_pct"] is not None else "—"
        print(f"  {z:<18} {b['made']:>5}/{b['att']:<5}  {pct}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
