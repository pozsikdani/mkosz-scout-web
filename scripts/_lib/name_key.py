"""Shared player-name normalization for cross-table dedup.

DB stores player names inconsistently (UPPER vs Title Case, occasional `?`
substitution for failed Ő-encoding, occasional 3rd-name truncation). All
exports must use the same dedup key so that team-shots, team-players, and
team-player-shots agree on identity — otherwise Svelte each_key_duplicate
crashes blank the entire team page.
"""
from __future__ import annotations

import unicodedata


def norm_full(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def player_dedup_key(name: str) -> str:
    """Cross-table dedup key. Handles UPPER vs Title, `?→o` Ő-encoding glitch
    (e.g. PLEESZ GERG? vs Pleesz Gergő), and name truncation by using the
    first 2 words (e.g. INALEGWU MARCELL vs INALEGWU MARCELL SÁMUEL)."""
    n = norm_full(name).replace("?", "o")
    parts = n.split()
    if len(parts) >= 2:
        return " ".join(parts[:2])
    return parts[0] if parts else ""
