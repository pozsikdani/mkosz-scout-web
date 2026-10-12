#!/usr/bin/env python3
"""Export per-team, per-match lineup tracking with PTS+/PTS- and minutes.

For each PBP-available match, walks substitution + scoring events in order,
attributing minutes and points to the lineup currently on court. Outputs raw
per-match lineup rows so the frontend can aggregate across any selection of
matches (single match, last 8, full season, etc.).

Output: static/data/team-lineup-nrtg/{slug}.json
{
    "team": "Vasas Akadémia",
    "season": "x2526",
    "match_count": 14,
    "matches": [
        {
            "gamecode": "hun2a_123471",
            "comp_code": "hun2a",
            "phase": "alapszakasz",
            "date": "2025-09-21",
            "opponent": "...",
            "home": true,
            "result": "W",
            "our_score": 89, "their_score": 70,
            "has_pbp": true,
            "starters": ["Bérces", "Farkas", ...],   // sorted canonical names
            "lineups": [
                {"players": ["A","B","C","D","E"], "min": 12.5, "pf": 24, "pa": 18, "is_starter": true,
                 "opp": [[min, pf, pa] × 6]}  // index = opponent starters on court (0..5), null if unknown
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
DEFAULT_OUT_DIR = REPO_ROOT / "static" / "data" / "team-lineup-nrtg"

COMPS: tuple[str, ...] = ("hun2a", "hun2a_ply", "hun2a_plya")  # overridden in main() from --comp
PHASE_MAP = {
    "hun2a": "alapszakasz",
    "hun2a_ply": "rajatszas_felso",
    "hun2a_plya": "rajatszas_also",
    "hun2b": "alapszakasz",
    "hun2b_ply": "rajatszas_felso",
    "hun2b_plya": "rajatszas_also",
}

TEAM_ALIASES: dict[str, list[str]] = {
    "EBH-Salgótarján": ["Salgótarjáni KSE"],
}


def norm_full(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def team_matches(canonical_name: str, db_name: str, aliases: list[str]) -> bool:
    db_full = norm_full(db_name)
    if len(db_full) < 4:
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
    """Merge-key: lowercase, accent-strip, `?→o` (failed Ő encoding),
    take first 2 words (handles "INALEGWU MARCELL" + "INALEGWU MARCELL SÁMUEL")."""
    n = norm_full(name).replace("?", "o")
    parts = n.split()
    if len(parts) >= 2:
        return " ".join(parts[:2])
    return parts[0] if parts else ""


def canonicalize(forms: Counter) -> str:
    """Pick canonical display form: most frequent, prefer non-UPPER on ties."""
    ranked = sorted(forms.items(), key=lambda kv: ("?" in kv[0], -len(kv[0]), kv[0].isupper(), -kv[1]))
    canon = ranked[0][0]
    if canon.isupper():
        canon = " ".join(p.capitalize() for p in canon.split())
    return canon


def build_name_canon_map(
    conn: sqlite3.Connection, gamecode: str, team_side: str
) -> dict[str, str]:
    """name_key → canonical display name, drawing from PBP events + subs + scoresheet."""
    forms: dict[str, Counter] = defaultdict(Counter)
    for n, in conn.execute(
        "SELECT player_in_name FROM substitutions WHERE gamecode=? AND team=? AND player_in_name IS NOT NULL",
        (gamecode, team_side),
    ):
        forms[name_key(n)][n] += 1
    for n, in conn.execute(
        "SELECT player_out_name FROM substitutions WHERE gamecode=? AND team=? AND player_out_name IS NOT NULL",
        (gamecode, team_side),
    ):
        forms[name_key(n)][n] += 1
    for n, in conn.execute(
        "SELECT player_name FROM player_game_stats WHERE gamecode=? AND team=? AND player_name IS NOT NULL",
        (gamecode, team_side),
    ):
        forms[name_key(n)][n] += 1
    return {k: canonicalize(v) for k, v in forms.items()}


def get_starters(
    conn: sqlite3.Connection, gamecode: str, team_side: str
) -> set[str] | None:
    """Return name_keys of the 5 starters.

    Primary: scoresheet `player_game_stats.is_starter=1` (megbízható, mindig 5).
    Fallback: PBP first-action-is-OUT heurisztika.
    """
    rows = conn.execute(
        """SELECT player_name FROM player_game_stats
           WHERE gamecode=? AND team=? AND is_starter=1 AND player_name IS NOT NULL""",
        (gamecode, team_side),
    ).fetchall()
    keys = {name_key(n) for (n,) in rows if n}
    if len(keys) == 5:
        return keys

    # Fallback: PBP heuristic (egyes meccseken nincs scoresheet starter info)
    sub_rows = conn.execute(
        """SELECT event_seq, player_in_name, player_out_name
           FROM substitutions WHERE gamecode=? AND team=? ORDER BY event_seq""",
        (gamecode, team_side),
    ).fetchall()
    seen: set[int] = set()
    fi: dict[str, int] = {}
    fo: dict[str, int] = {}
    for seq, in_n, out_n in sub_rows:
        if seq in seen:
            continue
        seen.add(seq)
        if in_n:
            k = name_key(in_n)
            fi.setdefault(k, seq)
        if out_n:
            k = name_key(out_n)
            fo.setdefault(k, seq)
    starters: set[str] = set()
    for k, fo_seq in fo.items():
        if fi.get(k, 10**9) > fo_seq:
            starters.add(k)
    if len(starters) == 5:
        return starters
    return None


def compute_match_lineups(
    conn: sqlite3.Connection, gamecode: str, team_side: str
) -> tuple[set[str], list[dict]] | None:
    """Replay PBP events and return (starter_keys, lineup_rows).

    lineup_rows = [{"players_keys": frozenset, "min": float, "pf": int, "pa": int}]
    Only rows with min > 0 OR scoring events recorded.
    """
    starters = get_starters(conn, gamecode, team_side)
    if starters is None:
        return None
    opp_side = "B" if team_side == "A" else "A"
    opp_starters = get_starters(conn, gamecode, opp_side)

    # Subs for both teams (deduped by event_seq per team)
    sub_rows = conn.execute(
        """
        SELECT event_seq, quarter, minute, team, player_in_name, player_out_name
        FROM substitutions
        WHERE gamecode=?
        ORDER BY event_seq
        """,
        (gamecode,),
    ).fetchall()
    seen_subs: set[tuple[int, str]] = set()
    sub_events = []
    for seq, q, mn, tm, in_n, out_n in sub_rows:
        if (seq, tm) in seen_subs or not (in_n and out_n):
            continue
        seen_subs.add((seq, tm))
        gt = mn or 0  # minute is cumulative game time (1-40, OT 41+)
        kind = "sub" if tm == team_side else "osub"
        sub_events.append((seq, kind, gt, name_key(in_n), name_key(out_n), 0, None))

    # Scoring events for both teams
    score_rows = conn.execute(
        """
        SELECT event_seq, quarter, minute, team, points
        FROM pbp_events
        WHERE gamecode=? AND points > 0
        ORDER BY event_seq
        """,
        (gamecode,),
    ).fetchall()
    score_events = []
    for seq, q, mn, tm, pts in score_rows:
        gt = mn or 0  # minute is cumulative game time (1-40, OT 41+)
        score_events.append((seq, "score", gt, None, None, pts, tm))

    all_ev = sorted(sub_events + score_events, key=lambda x: x[0])

    # Determine total game length (handle OT)
    max_q = 4
    if all_ev:
        # find max quarter from events
        max_q_row = conn.execute(
            "SELECT MAX(quarter) FROM pbp_events WHERE gamecode=?", (gamecode,)
        ).fetchone()
        if max_q_row and max_q_row[0]:
            max_q = max(4, int(max_q_row[0]))
    end_time = 40
    if max_q > 4:
        end_time = 40 + (max_q - 4) * 5

    on_court = set(starters)
    opp_on = set(opp_starters) if opp_starters else set()
    last_t = 0.0
    stats: dict[frozenset, dict] = defaultdict(
        lambda: {"min": 0.0, "pf": 0, "pa": 0, "opp": [[0.0, 0, 0] for _ in range(6)]}
    )

    def opp_bucket() -> int:
        return min(len(opp_on & opp_starters), 5) if opp_starters else 0

    def add_time(t: float) -> None:
        nonlocal last_t
        dt = max(t - last_t, 0)
        s = stats[frozenset(on_court)]
        s["min"] += dt
        s["opp"][opp_bucket()][0] += dt
        last_t = max(last_t, t)

    for seq, typ, gt, in_k, out_k, pts, tm in all_ev:
        if typ == "sub":
            add_time(gt)
            on_court.discard(out_k)
            on_court.add(in_k)
        elif typ == "osub":
            add_time(gt)
            opp_on.discard(out_k)
            opp_on.add(in_k)
        else:  # score
            s = stats[frozenset(on_court)]
            b = s["opp"][opp_bucket()]
            if tm == team_side:
                s["pf"] += pts
                b[1] += pts
            else:
                s["pa"] += pts
                b[2] += pts

    add_time(end_time)

    # Filter degenerate lineups (less than 5 — happens with foul-outs / data gaps)
    rows = []
    for lk, s in stats.items():
        if len(lk) != 5:
            continue
        if s["min"] <= 0 and s["pf"] == 0 and s["pa"] == 0:
            continue
        rows.append({
            "players_keys": lk,
            "min": round(s["min"], 1),
            "pf": s["pf"],
            "pa": s["pa"],
            # [min, pf, pa] by number of opponent starters on court (index 0..5);
            # None when the opponent's starting five is unknown.
            "opp": [[round(m, 1), pf, pa] for m, pf, pa in s["opp"]] if opp_starters else None,
        })
    return starters, rows


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--standings", default=None)
    p.add_argument("--out-dir", default=None)
    p.add_argument("--season", default="x2627")
    p.add_argument("--comp", default="hun2a")
    args = p.parse_args()
    if args.standings is None:
        args.standings = str(REPO_ROOT / "static" / "data" / args.season / "standings" / f"{args.comp}.json")
    if args.out_dir is None:
        args.out_dir = str(REPO_ROOT / "static" / "data" / args.season / "team-lineup-nrtg" / args.comp)
    global COMPS
    COMPS = (args.comp, f"{args.comp}_ply", f"{args.comp}_plya")


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
                continue
            if not has_pbp:
                continue  # no PBP = no lineup tracking
            team_side = "A" if is_a else "B"
            home = is_a
            opp = tb if is_a else ta
            our = sa if is_a else sb
            their = sb if is_a else sa
            result = "W" if our > their else ("L" if our < their else "D")

            res = compute_match_lineups(conn, gc, team_side)
            if res is None:
                continue
            starter_keys, lineup_rows = res

            canon_map = build_name_canon_map(conn, gc, team_side)

            # Resolve canonical names + sort
            def short_last(n: str) -> str:
                # We use last name only for compactness (matches mockup style)
                # But export full canonical name; UI can shorten.
                return n

            def to_names(keys: frozenset) -> list[str]:
                names = [canon_map.get(k, k.title()) for k in keys]
                return sorted(names)

            starter_names = to_names(starter_keys)
            out_lineups = []
            for r in lineup_rows:
                names = to_names(r["players_keys"])
                out_lineups.append({
                    "players": names,
                    "min": r["min"],
                    "pf": r["pf"],
                    "pa": r["pa"],
                    "is_starter": r["players_keys"] == starter_keys,
                    "opp": r["opp"],
                })
            # Sort by minutes desc for stable output
            out_lineups.sort(key=lambda x: -x["min"])

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
                "has_pbp": True,
                "starters": starter_names,
                "lineups": out_lineups,
            })

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
        total_lu = sum(len(m["lineups"]) for m in team_matches_out)
        print(f"  {team:<40} → {len(team_matches_out)} meccs, {total_lu} lineup-row")

    conn.close()
    print(f"\nÖsszesen: {written} fájl → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
