"""Fog climatology for the world's great fog coasts, from ERA5 via Open-Meteo.

No API key needed. For each site, pulls ten years of hourly low-cloud cover and
2 m relative humidity and counts "fog hours": hours when low cloud is thick
(>= LOW_CLOUD_MIN %) and the air near the ground is close to saturated
(>= RH_MIN %). That catches fog and the low stratus deck that becomes fog when
it touches the land (Namib coastal fog, Atacama camanchaca, San Francisco's
marine layer). ERA5 is a ~25 km reanalysis grid, so treat it as a regional
fog signal, not a station record.

Writes docs/data/fog.json for the landing page.
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timezone
from pathlib import Path

import requests

API = "https://archive-api.open-meteo.com/v1/archive"
OUT = Path(__file__).resolve().parents[1] / "docs" / "data" / "fog.json"

LOW_CLOUD_MIN = 70  # %
RH_MIN = 95  # %
START = "2016-01-01"
END = f"{date.today().year - 1}-12-31"  # last full calendar year

# km_coast: distance to the Natural Earth 1:10m coastline, computed once.
SITES = [
    # Namib: named places
    {"id": "walvis", "name": "Walvis Bay", "region": "Namib", "lat": -22.957, "lon": 14.505, "km_coast": 2},
    {"id": "swakop", "name": "Swakopmund", "region": "Namib", "lat": -22.678, "lon": 14.527, "km_coast": 0},
    {"id": "gobabeb", "name": "Gobabeb", "region": "Namib", "lat": -23.561, "lon": 15.041, "km_coast": 56},
    {"id": "sossus", "name": "Sossusvlei", "region": "Namib", "lat": -24.726, "lon": 15.293, "km_coast": 52},
    # Other fog coasts
    {"id": "patache", "name": "Alto Patache", "region": "Atacama", "lat": -20.82, "lon": -70.15, "km_coast": 3},
    {"id": "goldengate", "name": "Golden Gate", "region": "California", "lat": 37.81, "lon": -122.48, "km_coast": 0},
]
# Namib transect: due east from the coast along Gobabeb's latitude
TRANSECT = [(14.6, 11), (14.8, 31), (15.0, 51), (15.2, 72), (15.4, 92), (15.6, 112), (15.8, 133), (16.0, 153)]
for lon, km in TRANSECT:
    SITES.append({"id": f"t{km}", "name": f"{km} km inland", "region": "Namib transect",
                  "lat": -23.56, "lon": lon, "km_coast": km})


def fetch(site: dict) -> dict:
    for attempt in range(4):
        r = requests.get(API, params={
            "latitude": site["lat"], "longitude": site["lon"],
            "start_date": START, "end_date": END,
            "hourly": "cloud_cover_low,relative_humidity_2m",
            "timezone": "auto",
        }, timeout=180)
        if r.status_code == 429:
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()["hourly"]
    raise RuntimeError(f"rate-limited fetching {site['name']}")


def summarize(h: dict) -> dict:
    fog = [[0] * 24 for _ in range(12)]
    obs = [[0] * 24 for _ in range(12)]
    for t, low, rh in zip(h["time"], h["cloud_cover_low"], h["relative_humidity_2m"]):
        if low is None or rh is None:
            continue
        m, hr = int(t[5:7]) - 1, int(t[11:13])
        obs[m][hr] += 1
        if low >= LOW_CLOUD_MIN and rh >= RH_MIN:
            fog[m][hr] += 1
    pct = lambda f, n: round(100 * f / n, 1) if n else None
    monthly = [pct(sum(fog[m]), sum(obs[m])) for m in range(12)]
    return {
        "annual_pct": pct(sum(map(sum, fog)), sum(map(sum, obs))),
        "monthly_pct": monthly,
        "hour_by_month_pct": [[pct(fog[m][h], obs[m][h]) for h in range(24)] for m in range(12)],
    }


def main() -> None:
    out = []
    for s in SITES:
        stats = summarize(fetch(s))
        out.append({**s, **stats})
        print(f"{s['name']:<18} {s['region']:<15} fog {stats['annual_pct']:>5}% of hours")
        time.sleep(8)  # stay well under Open-Meteo's per-minute limit
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "period": [START, END],
        "source": "ERA5 reanalysis via Open-Meteo (open-meteo.com)",
        "fog_rule": {"low_cloud_min_pct": LOW_CLOUD_MIN, "rh2m_min_pct": RH_MIN},
        "sites": out,
    }, separators=(",", ":")))
    print(f"✓ {len(out)} sites → {OUT.relative_to(OUT.parents[2])}")


if __name__ == "__main__":
    main()
