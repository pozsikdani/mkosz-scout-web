#!/usr/bin/env python3
"""Export per-team, per-match starting fives + sub chains.

For each team, for every game played, emits:
- the 5 starters (from player_game_stats.is_starter=1)
- per-starter: jersey, minutes, points, REB, AST in that game
- per-starter: top substitutes (player_in when this starter was player_out)

The substitutions table has heavy row duplication (every event_seq has ~14
identical rows from repeat import/normalization). We dedupe by
(gamecode, event_seq).

Output: static/data/team-lineups/{slug}.json
{
    "team": "Vasas Akadémia",
    "season": "x2526",
    "matches": [
        {
            "gamecode": "hun2a_123471",
            "phase": "alapszakasz",
            "date": "2025-09-21",
            "opponent": "...",
            "home": true,
            "result": "W",
            "our_score": 89, "their_score": 70,
            "has_subs": true,           // PBP available for this comp
            "starters": [
                {
                    "name": "Fekete Viktor Norbert",
                    "jersey": 7,
                    "minutes": 32,
                    "points": 17, "reb": 5, "ast": 4,
                    "subs": [
                        {"name": "Pleesz Gergő", "jersey": 6, "count": 2}
                    ]
                }
            ]
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
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO_ROOT.parent / "mkosz-stats" / "mkosz_stats.sqlite"
DEFAULT_STANDINGS = REPO_ROOT / "static" / "data" / "standings" / "hun2a.json"
DEFAULT_OUT_DIR = REPO_ROOT / "static" / "data" / "team-lineups"

COMPS = ("hun2a", "hun2a_ply", "hun2a_plya")
PHASE_MAP = {
    "hun2a": "alapszakasz",
    "hun2a_ply": "rajatszas_felso",
    "hun2a_plya": "rajatszas_also",
}

TEAM_ALIASES: dict[str, list[str]] = {
    "EBH-Salgótarján": ["Salgótarjáni KSE"],
}


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


def name_key(name: str) -> str:
    """Merge-key for cross-table dedup.

    Handles three cases of scoresheet/PBP duplicates for the same player:
    1. UPPER vs Title case (already handled by norm_full lowercasing)
    2. `?` encoding glitch where `Ő` failed to decode (e.g. SEB?K vs SEBŐK,
       HEIMANN GERG? vs HEIMANN GERGŐ) — substitute `?` with `o` (the
       lowercased ő after accent strip)
    3. Name truncation (INALEGWU MARCELL vs INALEGWU MARCELL SÁMUEL) — only
       use the first 2 words as key
    """
    n = norm_full(name).replace("?", "o")
    parts = n.split()
    if len(parts) >= 2:
        return " ".join(parts[:2])
    return parts[0] if parts else ""


def fetch_starters_for_game(
    conn: sqlite3.Connection, gamecode: str, team_side: str
) -> list[dict]:
    """Return up to 5 starters for one team in one game."""
    # Dedup at (gamecode, name_key) — DB has UPPER+Title duplicates
    rows = conn.execute(
        """
        SELECT player_name, jersey_number, minutes, points,
               oreb, dreb, assists, is_starter
        FROM player_game_stats
        WHERE gamecode = ? AND team = ? AND is_starter = 1
        """,
        (gamecode, team_side),
    ).fetchall()

    by_key: dict[str, dict] = {}
    name_counts: dict[str, Counter] = defaultdict(Counter)
    for name, jersey, minutes, pts, oreb, dreb, ast, _ in rows:
        if not name:
            continue
        k = name_key(name)
        name_counts[k][name] += 1
        if k in by_key:
            # Merge: scoresheet often splits a player's stats across multiple
            # rows with name variants. Take max() of each numeric field, prefer
            # non-null jersey. (Identical UPPER+Title rows max to the same
            # value, so this is safe for that case too.)
            ex = by_key[k]
            ex["jersey"] = ex["jersey"] or jersey
            ex["minutes"] = max(ex["minutes"], int(minutes or 0))
            ex["points"] = max(ex["points"], int(pts or 0))
            ex["reb"] = max(ex["reb"], int((oreb or 0) + (dreb or 0)))
            ex["ast"] = max(ex["ast"], int(ast or 0))
            continue
        by_key[k] = {
            "_key": k,
            "name": name,
            "jersey": jersey,
            "minutes": int(minutes or 0),
            "points": int(pts or 0),
            "reb": int((oreb or 0) + (dreb or 0)),
            "ast": int(ast or 0),
        }
    # Pick the canonical name form: longest (captures full name), then prefer
    # non-UPPER, then most-frequent.
    out = []
    for k, p in by_key.items():
        forms = name_counts[k]
        # Canonical: avoid `?` placeholder, prefer longest, then non-UPPER, then count
        ranked = sorted(
            forms.items(),
            key=lambda kv: ("?" in kv[0], -len(kv[0]), kv[0].isupper(), -kv[1]),
        )
        canon = ranked[0][0]
        if canon.isupper():
            canon = " ".join(part.capitalize() for part in canon.split())
        p["name"] = canon
        out.append(p)
    # Cap at 5 (sanity — sometimes scoresheet has weird is_starter assignments)
    out = out[:5]
    return out


def fetch_subs_for_game(
    conn: sqlite3.Connection, gamecode: str, team_side: str
) -> dict[str, list[tuple[str, int]]]:
    """Return {starter_name_key: [(sub_name, count), ...]} for one game.

    Aggregates by player_out (starter) → counts of distinct player_in events.
    De-dupes the substitutions row dup at (gamecode, event_seq).
    """
    rows = conn.execute(
        """
        SELECT event_seq, player_in_name, player_out_name
        FROM substitutions
        WHERE gamecode = ? AND team = ?
        """,
        (gamecode, team_side),
    ).fetchall()

    # Dedup by event_seq, keep first
    seen: set[int] = set()
    events: list[tuple[str, str]] = []
    for seq, in_name, out_name in rows:
        if seq in seen:
            continue
        seen.add(seq)
        if in_name and out_name:
            events.append((in_name, out_name))

    # Group by out player
    by_out: dict[str, Counter] = defaultdict(Counter)
    sub_name_forms: dict[str, Counter] = defaultdict(Counter)
    for in_name, out_name in events:
        out_k = name_key(out_name)
        in_k = name_key(in_name)
        by_out[out_k][in_k] += 1
        sub_name_forms[in_k][in_name] += 1

    result: dict[str, list[tuple[str, int]]] = {}
    for out_k, in_counts in by_out.items():
        subs = []
        for in_k, count in in_counts.most_common():
            forms = sub_name_forms[in_k]
            ranked = sorted(forms.items(), key=lambda kv: (-kv[1], kv[0].isupper()))
            canon = ranked[0][0]
            if canon.isupper():
                canon = " ".join(p.capitalize() for p in canon.split())
            subs.append((canon, count))
        result[out_k] = subs
    return result


def build_player_lookup(conn: sqlite3.Connection, gamecode: str, team_side: str) -> dict[str, dict]:
    """Map name_key → {jersey, minutes, name} for one team in one game.

    Merge variants like SEB?K ANDRÁS / SEBŐK ANDRÁS / INALEGWU MARCELL /
    INALEGWU MARCELL SÁMUEL: max() of numeric fields, prefer non-null jersey,
    canonical display name without `?` and full-length.
    """
    rows = conn.execute(
        """SELECT player_name, jersey_number, minutes
           FROM player_game_stats
           WHERE gamecode=? AND team=?""",
        (gamecode, team_side),
    ).fetchall()
    name_forms: dict[str, Counter] = defaultdict(Counter)
    out: dict[str, dict] = {}
    for name, jersey, minutes in rows:
        if not name:
            continue
        k = name_key(name)
        name_forms[k][name] += 1
        if k in out:
            ex = out[k]
            ex["jersey"] = ex["jersey"] or jersey
            ex["minutes"] = max(ex["minutes"], int(minutes or 0))
        else:
            out[k] = {"jersey": jersey, "minutes": int(minutes or 0)}

    # Pick canonical display name per key
    for k, p in out.items():
        forms = name_forms[k]
        ranked = sorted(
            forms.items(),
            key=lambda kv: ("?" in kv[0], -len(kv[0]), kv[0].isupper(), -kv[1]),
        )
        canon = ranked[0][0]
        if canon.isupper():
            canon = " ".join(part.capitalize() for part in canon.split())
        p["name"] = canon
    return out


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

        team_matches_out: list[dict] = []
        for gc, comp, mdate, ta, tb, sa, sb, has_pbp in match_rows:
            is_a = team_matches(team, ta, aliases)
            is_b = team_matches(team, tb, aliases)
            if not (is_a or is_b):
                continue
            if not (sa and sb):
                continue  # only played games
            team_side = "A" if is_a else "B"
            home = is_a
            opp = tb if is_a else ta
            our = sa if is_a else sb
            their = sb if is_a else sa
            result = "W" if our > their else ("L" if our < their else "D")

            starters = fetch_starters_for_game(conn, gc, team_side)
            if not starters:
                continue  # scoresheet likely missing

            has_subs = bool(has_pbp)
            sub_chains: dict[str, list[tuple[str, int]]] = (
                fetch_subs_for_game(conn, gc, team_side) if has_subs else {}
            )
            player_lookup = build_player_lookup(conn, gc, team_side)
            for s in starters:
                k = s.pop("_key")
                subs = sub_chains.get(k, [])
                enriched = []
                for sub_name, count in subs[:3]:
                    info = player_lookup.get(name_key(sub_name), {})
                    # Prefer canonical display name from player_lookup (scoresheet)
                    # over raw PBP form (which may contain `?` for failed Ő encoding)
                    display_name = info.get("name") or sub_name
                    enriched.append({
                        "name": display_name,
                        "jersey": info.get("jersey"),
                        "minutes": info.get("minutes", 0),
                        "count": count,
                    })
                s["subs"] = enriched

            team_matches_out.append({
                "gamecode": gc,
                "comp_code": comp,
                "phase": PHASE_MAP.get(comp, comp),
                "date": mdate,
                "opponent": opp,
                "home": home,
                "result": result,
                "our_score": our,
                "their_score": their,
                "has_subs": has_subs,
                "starters": starters,
            })

        # newest first for the scrubber UI
        team_matches_out.sort(key=lambda m: (m["date"] or "", m["gamecode"]), reverse=True)

        payload = {
            "team": team,
            "season": args.season,
            "match_count": len(team_matches_out),
            "matches": team_matches_out,
        }
        out_path = out_dir / f"{slugify(team)}.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written += 1
        with_subs = sum(1 for m in team_matches_out if m["has_subs"])
        print(f"  {team:<40} → {len(team_matches_out)} meccs ({with_subs} sub adattal)")

    conn.close()
    print(f"\nÖsszesen: {written} fájl → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
