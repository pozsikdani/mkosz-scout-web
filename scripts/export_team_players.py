#!/usr/bin/env python3
"""Export per-team player season stats from mkosz_stats.sqlite to JSON.

For each team in standings/hun2a.json, aggregates player_game_stats across
the season (alapszakasz + rájátszás), computes per-player season averages,
and includes league-wide percentile ranks for each stat (used by the web
UI to show top/bottom 20% badges).

Output: static/data/team-players/{slug}.json
{
    "team": "Vasas Akadémia",
    "season": "x2526",
    "team_max_gp": 26,
    "players": [
        {
            "name": "Fekete Viktor Norbert",
            "jersey": 7,
            "gp": 24,
            "starts": 18,
            "gs_rate": 0.75,
            "mpg": 24.5, "ppg": 12.5, ...
            "fg_pct": 41.2, "three_pct": 27.0, "ft_pct": 70.0,
            "fg_made": 99, "fg_att": 257,
            "three_made": 35, "three_att": 126,
            "ft_made": 50, "ft_att": 70,
            "percentiles": { "ppg": 87, "rpg": 45, ... }
        }
    ]
}

Player-name dedup follows the same case-insensitive lower-key approach used
elsewhere — DB has e.g. "Fekete Viktor Norbert" + "FEKETE VIKTOR NORBERT" as
duplicates. We aggregate under the lower() key and pick the most common
display form as canonical.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib.name_key import norm_full, player_dedup_key  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT.parent / "mkosz-stats" / "mkosz_stats.sqlite"
DEFAULT_STANDINGS = REPO_ROOT / "static" / "data" / "standings" / "hun2a.json"
DEFAULT_OUT_DIR = REPO_ROOT / "static" / "data" / "team-players"
DEFAULT_ROSTERS = REPO_ROOT / "static" / "data" / "rosters" / "hun2a.json"

COMPS = ("hun2a", "hun2a_ply", "hun2a_plya")

TEAM_ALIASES: dict[str, list[str]] = {
    "EBH-Salgótarján": ["Salgótarjáni KSE"],
}

# League percentile thresholds — percentile only meaningful with enough sample
MIN_GP_FOR_PERCENTILE = 5
MIN_FGA = 50
MIN_3PA = 15
MIN_FTA = 10


def team_matches(canonical_name: str, db_name: str, aliases: list[str]) -> bool:
    db_full = norm_full(db_name)
    if len(db_full) < 5:
        return False
    for cand in [canonical_name, *aliases]:
        cand_full = norm_full(cand)
        cand_key = cand_full[:12]
        if cand_key in db_full or db_full in cand_full:
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


def roster_match_key(name: str) -> str:
    """Fuzzy name key for matching scoresheet/PBP names with roster names.

    Handles `?` encoding glitch (failed Ő → 'o') and accent strip; uses first
    2 words to handle name truncation (e.g. INALEGWU MARCELL vs INALEGWU
    MARCELL SÁMUEL).
    """
    n = norm_full(name).replace("?", "o")
    parts = n.split()
    if len(parts) >= 2:
        return " ".join(parts[:2])
    return parts[0] if parts else ""


def load_roster_lookup(rosters_path: Path) -> dict[tuple[str, str], dict]:
    """Build {(team_slug, name_match_key): {photo_filename, height_cm, position,
    birth_year, jersey, name}} from the rosters JSON.

    On match-key collision (siblings sharing first 2 words of name) the first
    wins — extremely rare, can revisit if observed.
    """
    if not rosters_path.exists():
        return {}
    rosters = json.loads(rosters_path.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], dict] = {}
    for team_slug, team in rosters.get("teams", {}).items():
        for pl in team.get("players", []):
            mk = roster_match_key(pl["name"])
            key = (team_slug, mk)
            if key in out:
                continue
            out[key] = {
                "photo_filename": pl.get("photo_filename"),
                "height_cm": pl.get("height_cm"),
                "position": pl.get("position"),
                "birth_year": pl.get("birth_year"),
                "jersey": pl.get("jersey"),
                "name": pl.get("name"),
            }
    return out


def aggregate_team_players(conn: sqlite3.Connection, team_name: str, season: str) -> dict:
    """Return {dedup_key: per-player aggregate dict} for the given team.

    The DB stores most rows twice (UPPER + Title Case forms); we de-dupe at
    the (gamecode, dedup_key) level so each game counts once per player.
    """
    aliases = TEAM_ALIASES.get(team_name, [])

    rows = conn.execute(
        f"""
        SELECT pgs.gamecode, pgs.player_name, pgs.jersey_number, pgs.is_starter, pgs.minutes,
               pgs.points, pgs.fg2_made, pgs.fg2_attempted,
               pgs.fg3_made, pgs.fg3_attempted, pgs.ft_made, pgs.ft_attempted,
               pgs.oreb, pgs.dreb, pgs.assists, pgs.steals,
               pgs.turnovers, pgs.blocks, pgs.fouls_drawn,
               pgs.personal_fouls,
               m.team_a_name, m.team_b_name, pgs.team
        FROM player_game_stats pgs
        JOIN matches m USING(gamecode)
        WHERE m.season = ?
          AND m.comp_code IN ({",".join("?" for _ in COMPS)})
        """,
        (season, *COMPS),
    ).fetchall()

    agg: dict[str, dict] = {}
    seen_game: set[tuple[str, str]] = set()
    for row in rows:
        (gamecode, name, jersey, is_starter, minutes, points,
         fg2m, fg2a, fg3m, fg3a, ftm, fta,
         oreb, dreb, ast, stl, tov, blk, fd, pf,
         team_a, team_b, team_side) = row

        is_a = team_matches(team_name, team_a, aliases)
        is_b = team_matches(team_name, team_b, aliases)
        if not ((team_side == "A" and is_a) or (team_side == "B" and is_b)):
            continue
        if not name:
            continue

        key = player_dedup_key(name)
        gk = (gamecode, key)
        if gk in seen_game:
            # duplicate row for the same (game, player) — skip
            # (still record the alternate name form for canonical-name picking)
            agg[key]["names"][name] += 1
            continue
        seen_game.add(gk)

        a = agg.setdefault(key, {
            "names": Counter(),
            "jerseys": Counter(),
            "gp": 0, "starts": 0,
            "min": 0, "pts": 0,
            "fg2m": 0, "fg2a": 0, "fg3m": 0, "fg3a": 0, "ftm": 0, "fta": 0,
            "oreb": 0, "dreb": 0, "ast": 0, "stl": 0,
            "tov": 0, "blk": 0, "fd": 0, "pf": 0,
        })
        a["names"][name] += 1
        if jersey is not None:
            a["jerseys"][jersey] += 1
        a["gp"] += 1
        a["starts"] += int(is_starter or 0)
        a["min"] += int(minutes or 0)
        a["pts"] += int(points or 0)
        a["fg2m"] += int(fg2m or 0); a["fg2a"] += int(fg2a or 0)
        a["fg3m"] += int(fg3m or 0); a["fg3a"] += int(fg3a or 0)
        a["ftm"] += int(ftm or 0); a["fta"] += int(fta or 0)
        a["oreb"] += int(oreb or 0); a["dreb"] += int(dreb or 0)
        a["ast"] += int(ast or 0); a["stl"] += int(stl or 0)
        a["tov"] += int(tov or 0); a["blk"] += int(blk or 0)
        a["fd"] += int(fd or 0); a["pf"] += int(pf or 0)
    return agg


def finalize_player(a: dict) -> dict:
    gp = max(1, a["gp"])
    fg_made = a["fg2m"] + a["fg3m"]
    fg_att = a["fg2a"] + a["fg3a"]
    canonical = a["names"].most_common(1)[0][0] if a["names"] else "?"
    # Title case if the only forms are all-caps
    if canonical.isupper():
        canonical = " ".join(p.capitalize() for p in canonical.split())
    jersey = a["jerseys"].most_common(1)[0][0] if a["jerseys"] else None
    return {
        "name": canonical,
        "jersey": jersey,
        "gp": a["gp"],
        "starts": a["starts"],
        "gs_rate": round(a["starts"] / gp, 3),
        "mpg": round(a["min"] / gp, 1),
        "ppg": round(a["pts"] / gp, 1),
        "rpg": round((a["oreb"] + a["dreb"]) / gp, 1),
        "oreb_pg": round(a["oreb"] / gp, 1),
        "dreb_pg": round(a["dreb"] / gp, 1),
        "apg": round(a["ast"] / gp, 1),
        "tpg": round(a["tov"] / gp, 1),
        "spg": round(a["stl"] / gp, 1),
        "bpg": round(a["blk"] / gp, 1),
        "fpg": round(a["pf"] / gp, 1),
        "fdpg": round(a["fd"] / gp, 1),
        "ato": round(a["ast"] / a["tov"], 2) if a["tov"] > 0 else None,
        "fg_made": fg_made, "fg_att": fg_att,
        "fg_pct": round(100 * fg_made / fg_att, 1) if fg_att > 0 else None,
        "three_made": a["fg3m"], "three_att": a["fg3a"],
        "three_pct": round(100 * a["fg3m"] / a["fg3a"], 1) if a["fg3a"] > 0 else None,
        "ft_made": a["ftm"], "ft_att": a["fta"],
        "ft_pct": round(100 * a["ftm"] / a["fta"], 1) if a["fta"] > 0 else None,
    }


# Stat keys to percentile-rank, with optional volume threshold
PERCENTILE_STATS = [
    ("ppg", None), ("rpg", None), ("oreb_pg", None), ("dreb_pg", None),
    ("apg", None), ("spg", None), ("bpg", None), ("fdpg", None),
    ("mpg", None),
    ("tpg", None),  # invert in UI (lower better)
    ("fpg", None),  # invert in UI
    ("fg_pct", "fg_att"), ("three_pct", "three_att"), ("ft_pct", "ft_att"),
]


def percentile_rank(values: list[float], v: float) -> int:
    """Standard percentile rank: % of values <= v, rounded to int."""
    if not values:
        return 50
    cnt = sum(1 for x in values if x <= v)
    return round(100 * cnt / len(values))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--standings", default=str(DEFAULT_STANDINGS))
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--rosters", default=str(DEFAULT_ROSTERS))
    p.add_argument("--season", default="x2526")
    args = p.parse_args()

    standings_path = Path(args.standings)
    if not standings_path.exists():
        print(f"ERROR: standings not found: {standings_path}", file=sys.stderr)
        return 1
    standings = json.loads(standings_path.read_text(encoding="utf-8"))
    teams = [t["team"] for t in standings["teams"]]
    roster_lookup = load_roster_lookup(Path(args.rosters))

    conn = sqlite3.connect(args.db)

    # Aggregate everyone first; then compute league percentile distribution.
    per_team_aggs: dict[str, dict] = {}
    for team in teams:
        per_team_aggs[team] = aggregate_team_players(conn, team, args.season)

    # Build league pools per stat (filtered by GP + per-stat volume threshold)
    league_pools: dict[str, list[float]] = defaultdict(list)
    flat_finals: dict[tuple[str, str], dict] = {}
    for team, agg in per_team_aggs.items():
        for key, a in agg.items():
            if a["gp"] < MIN_GP_FOR_PERCENTILE:
                continue
            f = finalize_player(a)
            flat_finals[(team, key)] = f
            for stat, vol_key in PERCENTILE_STATS:
                v = f.get(stat)
                if v is None:
                    continue
                # Volume threshold for shooting %
                if stat == "fg_pct" and (f.get("fg_att") or 0) < MIN_FGA: continue
                if stat == "three_pct" and (f.get("three_att") or 0) < MIN_3PA: continue
                if stat == "ft_pct" and (f.get("ft_att") or 0) < MIN_FTA: continue
                league_pools[stat].append(v)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for team, agg in per_team_aggs.items():
        team_slug = slugify(team)
        team_max_gp = max((a["gp"] for a in agg.values()), default=0)
        players: list[dict] = []
        for key, a in agg.items():
            f = finalize_player(a)
            # Cross-reference rosters JSON for photo + position + height + birth_year.
            # Roster jersey is authoritative — override scoresheet jersey if present.
            meta = roster_lookup.get((team_slug, roster_match_key(f["name"])))
            if meta:
                if meta.get("photo_filename"):
                    f["photo_filename"] = meta["photo_filename"]
                if meta.get("height_cm"):
                    f["height_cm"] = meta["height_cm"]
                if meta.get("position"):
                    f["position"] = meta["position"]
                if meta.get("birth_year"):
                    f["birth_year"] = meta["birth_year"]
                # jersey=0 is mkosz.hu placeholder for inactive/new players —
                # only override scoresheet jersey if roster has a real number.
                if meta.get("jersey"):
                    f["jersey"] = meta["jersey"]
                # Prefer the roster canonical (handles `?` / case variants)
                if meta.get("name"):
                    f["name"] = meta["name"]
            # Percentiles only for players who meet volume threshold
            pct = {}
            if a["gp"] >= MIN_GP_FOR_PERCENTILE:
                for stat, _ in PERCENTILE_STATS:
                    v = f.get(stat)
                    if v is None:
                        continue
                    if stat == "fg_pct" and (f.get("fg_att") or 0) < MIN_FGA: continue
                    if stat == "three_pct" and (f.get("three_att") or 0) < MIN_3PA: continue
                    if stat == "ft_pct" and (f.get("ft_att") or 0) < MIN_FTA: continue
                    pool = league_pools.get(stat, [])
                    pct[stat] = percentile_rank(pool, v)
            f["percentiles"] = pct
            players.append(f)

        # Sort: starters (gs_rate >= 0.5) first by ppg desc, then rotation by mpg desc
        def _sort_key(p):
            return (-(p["gs_rate"] or 0), -p["mpg"], -p["ppg"])
        players.sort(key=_sort_key)

        payload = {
            "team": team,
            "season": args.season,
            "team_max_gp": team_max_gp,
            "thresholds": {
                "min_gp_for_percentile": MIN_GP_FOR_PERCENTILE,
                "min_fga": MIN_FGA, "min_3pa": MIN_3PA, "min_fta": MIN_FTA,
            },
            "players": players,
        }
        out_path = out_dir / f"{slugify(team)}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written += 1
        print(f"  {team:<40} → {len(players)} játékos")

    conn.close()
    print(f"\nÖsszesen: {written} fájl → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
