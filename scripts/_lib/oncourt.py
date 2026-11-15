"""Pályán töltött idő alapú játékos-mutatók (Játékos-hatékonyság, 2. fázis).

Meccsenként végigjátssza a PBP-eseményeket és a cseréket (ugyanúgy, mint a
Lineup NRTG export), és minden eseményt jóváír a csapat épp pályán lévő
játékosainak. Ebből számolható pl. a USG% (a pályán töltött idő alatti
csapat-labdabirtoklásokhoz mérve), a lepattanó-arányok és az ON/OFF rating.

Labdabirtoklás: FGA + 0,44·FTA + TOV − OREB, a csapat-eseményekkel együtt
(mint a Liga összehasonlításban és a Lineup NRTG-ben). A játékos saját
számai csak a játékoshoz kötött eseményekből jönnek (= hivatalos box score).
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from typing import Callable

from export_team_lineup_nrtg import get_starters  # noqa: E402  (scripts/ a sys.path-on)

from _lib.name_key import player_dedup_key

FG2 = {"CLOSE_MADE", "CLOSE_MISS", "MID_MADE", "MID_MISS", "DUNK_MADE", "DUNK_MISS"}
FG3 = {"THREE_MADE", "THREE_MISS"}
FGA = FG2 | FG3
FGM = {"CLOSE_MADE", "MID_MADE", "DUNK_MADE", "THREE_MADE"}
FTA = {"FT_MADE", "FT_MISS"}

# Pályán-számlálók (csapat = mi, o_ = ellenfél), játékos-szintű saját számlálók
TEAM_KEYS = ("pf", "pa", "poss", "oposs", "fga", "fgm", "fta", "tov", "oreb", "dreb", "o_oreb", "o_dreb")
OWN_KEYS = ("pts", "fga", "fgm", "fg3a", "fta", "ftm", "tov", "ast", "oreb", "dreb", "stl", "blk", "fd",
            "fgm_ast",  # gólpasszból jött saját mezőnykosár
            "c_pts", "c_fga", "c_fta")  # szoros végjáték (c_): utolsó 5 perc + hosszabbítás, ±5 pont
CLUTCH_KEYS = ("pf", "pa", "poss", "oposs")


def _assist_pairs(evs: list) -> dict[int, str]:
    """{made-FG eseményindex: gólpasszt adó név}. A gólpassz a kosár mellett áll
    (többnyire előtte, néha utána); a legközelebbi, még nem párosított csapattárs-kosárhoz
    kötjük ±3 eseményen belül. A büntetőhöz adott gólpassz (FIBA) párosítatlan marad."""
    pairs: dict[int, str] = {}
    for i, (_, _, tm, pname, etype, _) in enumerate(evs):
        if etype != "AST" or not pname:
            continue
        for off in (-1, 1, -2, 2, -3, 3):
            j = i + off
            if 0 <= j < len(evs) and j not in pairs:
                _, _, tm2, p2, et2, _ = evs[j]
                if tm2 == tm and et2 in FGM and p2 and p2 != pname:
                    pairs[j] = pname
                    break
    return pairs


def _new_team() -> dict:
    return {k: 0.0 for k in TEAM_KEYS}


def _team_delta(etype: str, pts: int, ours: bool) -> dict:
    """Egy esemény hozzájárulása a (mi szemszögünkből vett) csapat-számlálókhoz."""
    d: dict[str, float] = {}
    poss = (1.0 if etype in FGA else 0.44 if etype in FTA else 1.0 if etype == "TOV"
            else -1.0 if etype == "OREB" else 0.0)
    if ours:
        if pts:
            d["pf"] = pts
        if poss:
            d["poss"] = poss
        if etype in FGA:
            d["fga"] = 1
        if etype in FGM:
            d["fgm"] = 1
        if etype in FTA:
            d["fta"] = 1
        if etype == "TOV":
            d["tov"] = 1
        if etype == "OREB":
            d["oreb"] = 1
        if etype == "DREB":
            d["dreb"] = 1
    else:
        if pts:
            d["pa"] = pts
        if poss:
            d["oposs"] = poss
        if etype == "OREB":
            d["o_oreb"] = 1
        if etype == "DREB":
            d["o_dreb"] = 1
    return d


def _own_delta(etype: str, pts: int) -> dict:
    d: dict[str, int] = {}
    if pts:
        d["pts"] = pts
    if etype in FGA:
        d["fga"] = 1
    if etype in FGM:
        d["fgm"] = 1
    if etype in FG3:
        d["fg3a"] = 1
    if etype in FTA:
        d["fta"] = 1
    if etype == "FT_MADE":
        d["ftm"] = 1
    for et, k in (("TOV", "tov"), ("AST", "ast"), ("OREB", "oreb"), ("DREB", "dreb"),
                  ("STL", "stl"), ("BLK", "blk"), ("FOUL_DRAWN", "fd")):
        if etype == et:
            d[k] = 1
    return d


def game_oncourt(conn: sqlite3.Connection, gamecode: str, side: str):
    """→ (team_total, {key: {"on": team-számlálók, "own": saját, "min": perc}}) vagy None."""
    starters = get_starters(conn, gamecode, side)
    if starters is None:
        return None

    subs = []
    seen: set[int] = set()
    for seq, mn, in_n, out_n in conn.execute(
        "SELECT event_seq, minute, player_in_name, player_out_name FROM substitutions "
        "WHERE gamecode=? AND team=? ORDER BY event_seq", (gamecode, side)
    ):
        if seq in seen or not (in_n and out_n):
            continue
        seen.add(seq)
        subs.append((seq, 0, "sub", mn or 0, player_dedup_key(in_n), player_dedup_key(out_n), 0))

    raw = conn.execute(
        "SELECT event_seq, minute, team, player_name, event_type, points FROM pbp_events "
        "WHERE gamecode=? ORDER BY event_seq", (gamecode,)
    ).fetchall()
    ast_pairs = _assist_pairs(raw)
    evs = []
    for idx, (seq, mn, tm, pname, etype, pts) in enumerate(raw):
        evs.append((seq, 1, "ev", mn or 0, tm, pname, (etype, pts or 0, idx)))

    max_q = conn.execute("SELECT MAX(quarter) FROM pbp_events WHERE gamecode=?", (gamecode,)).fetchone()[0] or 4
    end_time = 40 + max(0, int(max_q) - 4) * 5

    on = set(starters)
    score = {"A": 0, "B": 0}
    total = _new_team()
    players: dict[str, dict] = defaultdict(lambda: {
        "on": _new_team(), "own": {k: 0 for k in OWN_KEYS}, "min": 0.0,
        "clutch": {k: 0.0 for k in CLUTCH_KEYS},
        "ast_to": defaultdict(int),   # kinek adott gólpasszt (név-kulcs → db)
        "ast_by": defaultdict(int),   # kitől kapott gólpasszt
    })
    last_t = 0.0

    def add_time(t: float) -> None:
        nonlocal last_t
        dt = max(t - last_t, 0)
        for k in on:
            players[k]["min"] += dt
        last_t = max(last_t, t)

    for row in sorted(subs + evs, key=lambda r: (r[0], r[1])):
        if row[2] == "sub":
            _, _, _, gt, in_k, out_k, _ = row
            add_time(gt)
            on.discard(out_k)
            on.add(in_k)
            continue
        _, _, _, gt, tm, pname, (etype, pts, idx) = row
        ours = tm == side
        # Szoros végjáték: a 36. perctől (utolsó 5 perc) és hosszabbításban, ha az
        # esemény előtti állás legfeljebb 5 pont
        clutch = gt > 35 and abs(score[side] - score["B" if side == "A" else "A"]) <= 5
        delta = _team_delta(etype, pts, ours)
        for k, v in delta.items():
            total[k] += v
            for pk in on:
                players[pk]["on"][k] += v
                if clutch and k in CLUTCH_KEYS:
                    players[pk]["clutch"][k] += v
        if ours and pname:
            me = player_dedup_key(pname)
            own = players[me]["own"]
            for k, v in _own_delta(etype, pts).items():
                own[k] += v
                if clutch and k in ("pts", "fga", "fta"):
                    own["c_" + k] += v
            if idx in ast_pairs:
                giver = player_dedup_key(ast_pairs[idx])
                own["fgm_ast"] += 1
                players[me]["ast_by"][giver] += 1
                players[giver]["ast_to"][me] += 1
        if pts:
            score[tm] = score.get(tm, 0) + pts
    add_time(end_time)
    return total, dict(players)


def team_oncourt_season(
    conn: sqlite3.Connection,
    team_name: str,
    season: str,
    comps: tuple[str, ...],
    is_team: Callable[[str], bool],
):
    """Szezon-összesítés egy csapatra: (csapat-összes, {key: {"on", "own", "min", "gp"}})."""
    team_total = _new_team()
    agg: dict[str, dict] = {}
    for gc, ta, tb in conn.execute(
        f"""SELECT gamecode, team_a_name, team_b_name FROM matches
            WHERE season=? AND comp_code IN ({",".join("?" for _ in comps)})
              AND has_pbp=1 AND score_a IS NOT NULL AND score_a > 0""",
        (season, *comps),
    ).fetchall():
        side = "A" if is_team(ta) else "B" if is_team(tb) else None
        if side is None:
            continue
        res = game_oncourt(conn, gc, side)
        if res is None:
            continue
        total, players = res
        for k, v in total.items():
            team_total[k] += v
        for key, p in players.items():
            a = agg.setdefault(key, {
                "on": _new_team(), "own": {k: 0 for k in OWN_KEYS}, "min": 0.0, "gp": 0,
                "clutch": {k: 0.0 for k in CLUTCH_KEYS}, "ast_to": defaultdict(int), "ast_by": defaultdict(int),
            })
            for k, v in p["on"].items():
                a["on"][k] += v
            for k, v in p["own"].items():
                a["own"][k] += v
            for k, v in p["clutch"].items():
                a["clutch"][k] += v
            for k, v in p["ast_to"].items():
                a["ast_to"][k] += v
            for k, v in p["ast_by"].items():
                a["ast_by"][k] += v
            a["min"] += p["min"]
            a["gp"] += 1
    return team_total, agg


def _r(v: float | None, d: int = 1):
    return None if v is None else round(v, d)


def player_metrics(team_total: dict, a: dict) -> dict:
    """Arány- és /100 mutatók egy játékosra a pályán töltött idő alapján."""
    on, own = a["on"], a["own"]
    poss, oposs = on["poss"], on["oposs"]
    off_poss = team_total["poss"] - poss
    off_oposs = team_total["oposs"] - oposs
    plays = own["fga"] + 0.44 * own["fta"] + own["tov"]
    team_plays = on["fga"] + 0.44 * on["fta"] + on["tov"]

    def per100(x: float):
        return _r(100 * x / poss) if poss > 0 else None

    def rate(num: float, den: float):
        return _r(100 * num / den) if den > 0 else None

    on_o = 100 * on["pf"] / poss if poss > 0 else None
    on_d = 100 * on["pa"] / oposs if oposs > 0 else None
    off_o = 100 * (team_total["pf"] - on["pf"]) / off_poss if off_poss >= 1 else None
    off_d = 100 * (team_total["pa"] - on["pa"]) / off_oposs if off_oposs >= 1 else None
    on_n = on_o - on_d if on_o is not None and on_d is not None else None
    off_n = off_o - off_d if off_o is not None and off_d is not None else None

    return {
        "min_on": _r(a["min"]),
        "poss_on": _r(poss),
        "usg_pct": rate(plays, team_plays),
        "ast_pct": rate(own["ast"], on["fgm"] - own["fgm"]),
        "tov_pct": rate(own["tov"], plays),
        "oreb_pct": rate(own["oreb"], on["oreb"] + on["o_dreb"]),
        "dreb_pct": rate(own["dreb"], on["dreb"] + on["o_oreb"]),
        "pts_100": per100(own["pts"]),
        "reb_100": per100(own["oreb"] + own["dreb"]),
        "ast_100": per100(own["ast"]),
        "tov_100": per100(own["tov"]),
        "stl_100": per100(own["stl"]),
        "blk_100": per100(own["blk"]),
        "fd_100": per100(own["fd"]),
        "on_ortg": _r(on_o),
        "on_drtg": _r(on_d),
        "on_nrtg": _r(on_n),
        "off_ortg": _r(off_o),
        "off_drtg": _r(off_d),
        "off_nrtg": _r(off_n),
        "off_poss": _r(off_poss),
        # 3. fázis — gólpassz-párosítás és szoros végjáték
        "assisted_pct": rate(own["fgm_ast"], own["fgm"]),
        "clutch_poss": _r(a["clutch"]["poss"]),
        "clutch_pts": own["c_pts"],
        "clutch_ts": _r(100 * own["c_pts"] / (2 * (own["c_fga"] + 0.44 * own["c_fta"])))
        if (own["c_fga"] + own["c_fta"]) > 0 else None,
        "clutch_nrtg": _r(100 * a["clutch"]["pf"] / a["clutch"]["poss"] - 100 * a["clutch"]["pa"] / a["clutch"]["oposs"])
        if a["clutch"]["poss"] >= 1 and a["clutch"]["oposs"] >= 1 else None,
        "onoff_nrtg": _r(on_n - off_n) if on_n is not None and off_n is not None else None,
    }
