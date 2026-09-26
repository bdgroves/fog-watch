"""Gridded fog frequency for the three fog coasts (ERA5 via Open-Meteo, no key).

Samples ERA5 at its native 0.25° spacing over each region and applies the same
fog rule as fog_climatology.py (low cloud >= 70 %, 2 m RH >= 95 %) to the last
two full years of hourly data. Open-Meteo accepts many coordinates per request,
so cells go in small batches with pauses to stay inside the free tier.

Writes docs/data/fog_grid.json: per cell, annual and monthly % of foggy hours.
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from fog_climatology import API, LOW_CLOUD_MIN, RH_MIN

OUT = Path(__file__).resolve().parents[1] / "docs" / "data" / "fog_grid.json"
STEP = 0.25
LAST = date.today().year - 1
START, END = f"{LAST - 1}-01-01", f"{LAST}-12-31"
BATCH = 10

REGIONS = {
    "namib":      {"name": "Namib",      "lat": (-25.5, -21.0), "lon": (13.5, 16.25)},
    "atacama":    {"name": "Atacama",    "lat": (-22.5, -18.5), "lon": (-71.5, -69.5)},
    "california": {"name": "California", "lat": (36.5, 39.0),   "lon": (-124.0, -121.5)},
}

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "fog-watch (github.com/bdgroves/fog-watch)"


def frange(a: float, b: float, step: float) -> list[float]:
    n = int(round((b - a) / step))
    return [round(a + i * step, 4) for i in range(n + 1)]


def fetch_batch(cells: list[tuple[float, float]]) -> list[dict]:
    wait = 15
    for attempt in range(6):
        try:
            r = SESSION.get(API, params={
                "latitude": ",".join(str(c[0]) for c in cells),
                "longitude": ",".join(str(c[1]) for c in cells),
                "start_date": START, "end_date": END,
                "hourly": "cloud_cover_low,relative_humidity_2m",
                "timezone": "GMT",
            }, timeout=(15, 150))
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            js = r.json()
            return js if isinstance(js, list) else [js]
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            print(f"    retry {attempt + 1}: {e}")
            time.sleep(wait)
            wait = min(wait * 2, 180)
    raise RuntimeError("gave up on batch")


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


def main() -> None:
    out = {}
    for key, reg in REGIONS.items():
        cells = [(la, lo) for la in frange(*reg["lat"], STEP) for lo in frange(*reg["lon"], STEP)]
        rows = []
        for i in range(0, len(cells), BATCH):
            chunk = cells[i:i + BATCH]
            for (la, lo), res in zip(chunk, fetch_batch(chunk)):
                rows.append({"lat": la, "lon": lo, **cell_stats(res["hourly"])})
            print(f"  {reg['name']}: {min(i + BATCH, len(cells))}/{len(cells)} cells")
            time.sleep(12)
        out[key] = {"name": reg["name"], "step": STEP, "cells": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "period": [START, END],
        "fog_rule": {"low_cloud_min_pct": LOW_CLOUD_MIN, "rh2m_min_pct": RH_MIN},
        "regions": out,
    }, separators=(",", ":")))
    print(f"✓ {sum(len(r['cells']) for r in out.values())} cells → {OUT.name}")


if __name__ == "__main__":
    main()
