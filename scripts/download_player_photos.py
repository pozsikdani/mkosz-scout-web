#!/usr/bin/env python3
"""Download + crop player photos based on rosters JSON.

Reads `static/data/rosters/{comp}.json`, downloads each `photo_url`, square-
crops from the top (face-centric), resizes to 200×200, saves as JPG to
`static/players/{photo_filename}`. Idempotent: skips if file exists unless
--force is passed.
"""
from __future__ import annotations

import argparse
import json
import sys
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROSTERS = REPO_ROOT / "static" / "data" / "rosters" / "hun2a.json"
DEFAULT_OUT_DIR = REPO_ROOT / "static" / "players"

PHOTO_SIZE = 200


def crop_and_save(pic_url: str, out_path: Path, size: int = PHOTO_SIZE) -> bool:
    try:
        resp = requests.get(pic_url, timeout=15)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
    except Exception as e:
        print(f"    download fail {pic_url}: {e}", file=sys.stderr)
        return False
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    img = img.crop((left, 0, left + side, side))
    img = img.resize((size, size), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=85, optimize=True)
    return True


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--rosters", default=str(DEFAULT_ROSTERS))
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--force", action="store_true",
                   help="Re-download even if photo file already exists")
    args = p.parse_args()

    rosters = json.loads(Path(args.rosters).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    skipped = 0
    failed = 0
    for team_slug, team in rosters["teams"].items():
        for pl in team["players"]:
            url = pl.get("photo_url")
            fn = pl.get("photo_filename")
            if not (url and fn):
                continue
            out_path = out_dir / fn
            if out_path.exists() and not args.force:
                skipped += 1
                continue
            ok = crop_and_save(url, out_path)
            if ok:
                downloaded += 1
            else:
                failed += 1

    print(f"Letöltve: {downloaded}, skip (cache): {skipped}, hiba: {failed} → {out_dir}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
