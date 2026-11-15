"""Dobásminőség a lövéstérképből (Játékos-hatékonyság, 3. fázis).

Zónánként a liga átlagos pont/dobás értéke (= FG% × a zóna értéke), ebből:
- xPPS: a játékos dobásainak várható pontja dobásonként (a dobásválasztás minősége),
- PPS:  a ténylegesen szerzett pont dobásonként ugyanezeken a dobásokon,
- PPS − xPPS: mennyivel teljesít a liga-átlag felett a saját dobásaiból.

A zónák geometriája az export_team_player_shots.py-ból jön (= a Shotchart tab).
Büntetők nélkül; csak a lövéstérképpel rendelkező meccsek.
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict

from export_team_player_shots import classify_zone  # noqa: E402

from _lib.name_key import player_dedup_key

THREE_ZONES = {"corner3_l", "corner3_r", "wing3_l", "wing3_r", "above_break_3"}


def zone_value(zone: str) -> int:
    return 3 if zone in THREE_ZONES else 2


def _fetch(conn: sqlite3.Connection, season: str, comps: tuple[str, ...]):
    return conn.execute(
        f"""
        SELECT s.team_id, s.player_name, s.hx, s.hy, s.is_made
        FROM shots s JOIN matches m USING(gamecode)
        WHERE m.season = ? AND m.comp_code IN ({",".join("?" for _ in comps)})
          AND s.is_free_throw = 0 AND s.hx IS NOT NULL AND s.hy IS NOT NULL
          AND s.player_name IS NOT NULL AND s.player_name != ''
        """,
        (season, *comps),
    ).fetchall()


def league_shot_quality(conn: sqlite3.Connection, season: str, comps: tuple[str, ...]):
    """→ (zóna-baseline {zone: pps}, {(team_id, player_key): {"n", "xpts", "pts"}})."""
    rows = [(tid, name, classify_zone(float(hx), float(hy)), made) for tid, name, hx, hy, made in _fetch(conn, season, comps)]
    made = defaultdict(int)
    att = defaultdict(int)
    for _, _, z, m in rows:
        att[z] += 1
        made[z] += int(m or 0)
    pps = {z: zone_value(z) * made[z] / att[z] for z in att if att[z] > 0}

    per: dict[tuple[int, str], dict] = defaultdict(lambda: {"n": 0, "xpts": 0.0, "pts": 0})
    for tid, name, z, m in rows:
        a = per[(tid, player_dedup_key(name))]
        a["n"] += 1
        a["xpts"] += pps.get(z, 0.0)
        a["pts"] += zone_value(z) * int(m or 0)
    return pps, dict(per)


def player_shot_metrics(sq: dict | None) -> dict:
    if not sq or sq["n"] == 0:
        return {}
    n = sq["n"]
    xpps = sq["xpts"] / n
    act = sq["pts"] / n
    return {
        "chart_fga": n,
        "xpps": round(xpps, 3),
        "pps": round(act, 3),
        "pps_diff": round(act - xpps, 3),
    }
