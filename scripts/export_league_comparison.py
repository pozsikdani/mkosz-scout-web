#!/usr/bin/env python3
"""Export league-wide team aggregates for §1.6 League Comparison.

Computes per-team season totals (PBP-based) + standings PPG/OPPG, outputs a
single league-level JSON consumed by the frontend (one file for all teams,
the UI highlights the current team).

Output: static/data/league-comparison/hun2a.json
{
    "comp": "hun2a",
    "season": "x2526",
    "teams": [
        {
            "team": "Vasas Akadémia",
            "gp": 26,
            "ppg": 78.4, "oppg": 82.1, "nrtg": -3.7,
            "pace": 73.2,
            "fg_pct": 43.1, "tp_pct": 31.8, "ft_pct": 68.4,
            "rpg": 35.2, "oreb_pg": 11.4, "dreb_pg": 23.8,
            "apg": 14.1, "topg": 13.6, "spg": 7.8, "bpg": 1.2
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
DEFAULT_OUT_DIR = REPO_ROOT / "static" / "data" / "league-comparison"
DEFAULT_COMP = "hun2a"


def norm_full(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def merge_key(tn: str) -> str:
    """Match mockup _lc_merge_key — handle DB encoding/name variants."""
    k = tn.lower().replace("õ", "ő").replace("?", "ő").replace("-", " ")
    if "salgó" in k or "salg" in k:
        return "salgotarjan"
    if k.startswith("bkg prima"):
        return "bkg prima"
    return norm_full(k)[:12]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", default=str(DEFAULT_DB))
    p.add_argument("--standings", default=str(DEFAULT_STANDINGS))
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--comp", default=DEFAULT_COMP)
    p.add_argument("--season", default="x2526")
    args = p.parse_args()

    standings_path = Path(args.standings)
    if not standings_path.exists():
        print(f"ERROR: standings not found: {standings_path}", file=sys.stderr)
        return 1
    standings = json.loads(standings_path.read_text(encoding="utf-8"))
    canonical_teams = standings["teams"]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    # Aggregate PBP team stats (alapszakasz only — no playoff comps)
    rows = [dict(r) for r in conn.execute(
        """
        SELECT
            CASE WHEN e.team='A' THEN m.team_a_name ELSE m.team_b_name END AS team_name,
            COUNT(DISTINCT m.gamecode) AS gp,
            SUM(CASE WHEN e.event_type IN ('CLOSE_MADE','MID_MADE','DUNK_MADE','THREE_MADE') THEN 1 ELSE 0 END) AS fgm,
            SUM(CASE WHEN e.event_type IN ('CLOSE_MADE','CLOSE_MISS','MID_MADE','MID_MISS','DUNK_MADE','DUNK_MISS','THREE_MADE','THREE_MISS') THEN 1 ELSE 0 END) AS fga,
            SUM(CASE WHEN e.event_type='THREE_MADE' THEN 1 ELSE 0 END) AS tpm,
            SUM(CASE WHEN e.event_type IN ('THREE_MADE','THREE_MISS') THEN 1 ELSE 0 END) AS tpa,
            SUM(CASE WHEN e.event_type='FT_MADE' THEN 1 ELSE 0 END) AS ftm,
            SUM(CASE WHEN e.event_type IN ('FT_MADE','FT_MISS') THEN 1 ELSE 0 END) AS fta,
            SUM(CASE WHEN e.event_type='OREB' THEN 1 ELSE 0 END) AS oreb,
            SUM(CASE WHEN e.event_type IN ('OREB','DREB') THEN 1 ELSE 0 END) AS reb,
            SUM(CASE WHEN e.event_type='AST' THEN 1 ELSE 0 END) AS ast,
            SUM(CASE WHEN e.event_type='TOV' THEN 1 ELSE 0 END) AS tov,
            SUM(CASE WHEN e.event_type='STL' THEN 1 ELSE 0 END) AS stl,
            SUM(CASE WHEN e.event_type='BLK' THEN 1 ELSE 0 END) AS blk
        FROM pbp_events e
        JOIN matches m ON e.gamecode = m.gamecode
        WHERE m.comp_code = ?
          AND m.score_a > 0
          AND e.event_type != 'UNKNOWN'
        GROUP BY team_name
        """,
        (args.comp,),
    ).fetchall()]
    conn.close()

    # Merge encoding/name variants
    merged: dict[str, dict] = {}
    for r in rows:
        tn = r["team_name"]
        if not tn:
            continue
        k = merge_key(tn)
        if k in merged:
            ex = merged[k]
            for col in ("gp", "fgm", "fga", "tpm", "tpa", "ftm", "fta",
                        "oreb", "reb", "ast", "tov", "stl", "blk"):
                ex[col] = (ex[col] or 0) + (r[col] or 0)
            if len(tn) > len(ex["team_name"]):
                ex["team_name"] = tn
        else:
            merged[k] = dict(r)

    # Resolve canonical names from standings + compute per-game
    def find_canonical(db_name: str) -> dict | None:
        q = norm_full(db_name).replace("-", " ")
        for s in canonical_teams:
            sq = norm_full(s["team"]).replace("-", " ")
            if q[:10] in sq or sq[:10] in q:
                return s
        return None

    # Collapse merge-key duplicates that map to the same standings team
    # (handles odd encoding variants like 'A… HÜBNER NYÍREGYHÁZA BS' that
    # produce different merge_keys but the same canonical team).
    by_canon: dict[str, dict] = {}
    for r in merged.values():
        canon = find_canonical(r["team_name"])
        if not canon:
            continue
        ck = canon["team"]
        if ck in by_canon:
            ex = by_canon[ck]
            for col in ("gp", "fgm", "fga", "tpm", "tpa", "ftm", "fta",
                        "oreb", "reb", "ast", "tov", "stl", "blk"):
                ex[col] = (ex[col] or 0) + (r[col] or 0)
        else:
            by_canon[ck] = dict(r)

    out_teams: list[dict] = []
    for ck, r in by_canon.items():
        canon = next(s for s in canonical_teams if s["team"] == ck)
        gp = r["gp"] or 1
        st_gp = (canon.get("w") or 0) + (canon.get("l") or 0)
        if st_gp > 0 and canon.get("scored"):
            ppg = round(canon["scored"] / st_gp, 1)
            oppg = round((canon.get("allowed") or 0) / st_gp, 1)
        else:
            ppg = oppg = 0.0

        poss = (r["fga"] or 0) + 0.44 * (r["fta"] or 0) + (r["tov"] or 0) - (r["oreb"] or 0)
        out_teams.append({
            "team": canon["team"],
            "gp": int(r["gp"] or 0),
            "ppg": ppg,
            "oppg": oppg,
            "nrtg": round(ppg - oppg, 1),
            "pace": round(poss / gp, 1),
            "fg_pct": round((r["fgm"] or 0) * 100 / r["fga"], 1) if r["fga"] else 0.0,
            "tp_pct": round((r["tpm"] or 0) * 100 / r["tpa"], 1) if r["tpa"] else 0.0,
            "ft_pct": round((r["ftm"] or 0) * 100 / r["fta"], 1) if r["fta"] else 0.0,
            "rpg": round((r["reb"] or 0) / gp, 1),
            "oreb_pg": round((r["oreb"] or 0) / gp, 1),
            "dreb_pg": round(((r["reb"] or 0) - (r["oreb"] or 0)) / gp, 1),
            "apg": round((r["ast"] or 0) / gp, 1),
            "topg": round((r["tov"] or 0) / gp, 1),
            "spg": round((r["stl"] or 0) / gp, 1),
            "bpg": round((r["blk"] or 0) / gp, 1),
        })

    out_teams.sort(key=lambda t: -t["nrtg"])
    payload = {
        "comp": args.comp,
        "season": args.season,
        "team_count": len(out_teams),
        "teams": out_teams,
    }
    out_path = out_dir / f"{args.comp}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  League comparison ({args.comp}): {len(out_teams)} csapat → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
