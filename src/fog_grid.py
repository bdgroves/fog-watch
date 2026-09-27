"""Gridded fog frequency for the fog coasts (ERA5 via Open-Meteo, no key).

Samples ERA5 at its native 0.25° spacing and applies the same fog rule as
fog_climatology.py (low cloud >= 70 %, 2 m RH >= 95 %) to the last full year
of hourly data.

Open-Meteo's free tier is metered in weighted calls: every location counts,
and a year of data weighs ~26 calls per location. Limits are 600/min,
5,000/hour and 10,000/day. So this script does ONE region per run (~1,200 to
3,000 weighted calls), paces itself, and merges into docs/data/fog_grid.json
so the other regions are kept.

Usage:  python src/fog_grid.py namib      (or atacama, california)
        python src/fog_grid.py auto       (picks by day of month: 4 → namib, 5 → atacama, 6 → california)
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from fog_climatology import API, LOW_CLOUD_MIN, RH_MIN

OUT = Path(__file__).resolve().parents[1] / "docs" / "data" / "fog_grid.json"
STEP = 0.25
YEAR = date.today().year - 1
START, END = f"{YEAR}-01-01", f"{YEAR}-12-31"
BATCH = 8                      # locations per request (~210 weighted calls)
PAUSE = 30                     # seconds between requests → ~420 calls/min, under 600

REGIONS = {
    # 13 × 9 = 117 cells: Walvis Bay / Swakopmund coast to ~130 km inland, Kuiseb to Sossusvlei
    "namib":      {"name": "Namib",      "lat": (-24.5, -21.5), "lon": (13.75, 15.75)},
    # 9 × 5 = 45 cells: Iquique coast and the Alto Patache fog oasis
    "atacama":    {"name": "Atacama",    "lat": (-21.5, -19.5), "lon": (-70.75, -69.75)},
    # 7 × 7 = 49 cells: Golden Gate, Marin, Point Reyes and the inner Bay
    "california": {"name": "California", "lat": (37.0, 38.5),   "lon": (-123.5, -122.0)},
}
AUTO = {4: "namib", 5: "atacama", 6: "california"}

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "fog-watch (github.com/bdgroves/fog-watch)"


def frange(a: float, b: float, step: float) -> list[float]:
    n = int(round((b - a) / step))
    return [round(a + i * step, 4) for i in range(n + 1)]


def fetch_batch(cells: list[tuple[float, float]]) -> list[dict]:
    for attempt in range(8):
        try:
            r = SESSION.get(API, params={
                "latitude": ",".join(str(c[0]) for c in cells),
                "longitude": ",".join(str(c[1]) for c in cells),
                "start_date": START, "end_date": END,
                "hourly": "cloud_cover_low,relative_humidity_2m",
                "timezone": "GMT",
            }, timeout=(15, 150))
            if r.status_code == 429:
                # minutely limit clears in a minute, hourly in up to an hour
                wait = 70 if attempt < 2 else 300
                print(f"    429 rate limit ({r.text[:120]!r}); waiting {wait}s")
                time.sleep(wait)
                continue
            if r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            js = r.json()
            return js if isinstance(js, list) else [js]
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            wait = min(15 * 2 ** attempt, 300)
            print(f"    retry {attempt + 1}: {e}; waiting {wait}s")
            time.sleep(wait)
    raise RuntimeError("gave up on batch after 8 attempts")


def cell_stats(h: dict) -> dict:
    fog, obs = [0] * 12, [0] * 12
    for t, low, rh in zip(h["time"], h["cloud_cover_low"], h["relative_humidity_2m"]):
        if low is None or rh is None:
            continue
        m = int(t[5:7]) - 1
        obs[m] += 1
        fog[m] += low >= LOW_CLOUD_MIN and rh >= RH_MIN
    pct = lambda f, n: round(100 * f / n, 1) if n else None
    return {"a": pct(sum(fog), sum(obs)), "m": [pct(fog[i], obs[i]) for i in range(12)]}


def run_region(key: str) -> dict:
    reg = REGIONS[key]
    cells = [(la, lo) for la in frange(*reg["lat"], STEP) for lo in frange(*reg["lon"], STEP)]
    print(f"{reg['name']}: {len(cells)} cells, {START} to {END}")
    rows = []
    for i in range(0, len(cells), BATCH):
        chunk = cells[i:i + BATCH]
        for (la, lo), res in zip(chunk, fetch_batch(chunk)):
            rows.append({"lat": la, "lon": lo, **cell_stats(res["hourly"])})
        print(f"  {len(rows)}/{len(cells)} cells")
        if i + BATCH < len(cells):
            time.sleep(PAUSE)
    return {"name": reg["name"], "step": STEP, "period": [START, END], "cells": rows}


def main() -> None:
    arg = (sys.argv[1] if len(sys.argv) > 1 else "auto").lower()
    key = AUTO.get(date.today().day, "namib") if arg == "auto" else arg
    if key not in REGIONS:
        raise SystemExit(f"unknown region {key!r}; choose from {', '.join(REGIONS)}")
    data = json.loads(OUT.read_text()) if OUT.exists() else {"regions": {}}
    data["regions"][key] = run_region(key)
    # keep regions in a stable order
    data["regions"] = {k: data["regions"][k] for k in REGIONS if k in data["regions"]}
    data.update({
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "period": [START, END],
        "fog_rule": {"low_cloud_min_pct": LOW_CLOUD_MIN, "rh2m_min_pct": RH_MIN},
    })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":")))
    print(f"✓ {key} merged → {OUT.name} (regions: {', '.join(data['regions'])})")


if __name__ == "__main__":
    main()
