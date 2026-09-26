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


SESSION = requests.Session()
SESSION.headers["User-Agent"] = "fog-watch (github.com/bdgroves/fog-watch)"


def fetch_year(site: dict, year: int) -> dict:
    """One calendar year of hourly data. Small requests: a 10-year pull timed out."""
    end = min(f"{year}-12-31", END)
    wait = 10
    for attempt in range(6):
        try:
            r = SESSION.get(API, params={
                "latitude": site["lat"], "longitude": site["lon"],
                "start_date": f"{year}-01-01", "end_date": end,
                "hourly": "cloud_cover_low,relative_humidity_2m",
                "timezone": "auto",
            }, timeout=(15, 90))
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json()["hourly"]
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            print(f"    retry {attempt + 1} for {site['name']} {year}: {e}")
            time.sleep(wait)
            wait = min(wait * 2, 120)
    raise RuntimeError(f"gave up on {site['name']} {year}")


def summarize(site: dict) -> dict:
    fog = [[0] * 24 for _ in range(12)]
    obs = [[0] * 24 for _ in range(12)]
    for year in range(int(START[:4]), int(END[:4]) + 1):
        h = fetch_year(site, year)
        for t, low, rh in zip(h["time"], h["cloud_cover_low"], h["relative_humidity_2m"]):
            if low is None or rh is None:
                continue
            m, hr = int(t[5:7]) - 1, int(t[11:13])
            obs[m][hr] += 1
            if low >= LOW_CLOUD_MIN and rh >= RH_MIN:
                fog[m][hr] += 1
        time.sleep(1.5)  # gentle on Open-Meteo's free tier
    pct = lambda f, n: round(100 * f / n, 1) if n else None
    return {
        "annual_pct": pct(sum(map(sum, fog)), sum(map(sum, obs))),
        "monthly_pct": [pct(sum(fog[m]), sum(obs[m])) for m in range(12)],
        "hour_by_month_pct": [[pct(fog[m][h], obs[m][h]) for h in range(24)] for m in range(12)],
    }


def main() -> None:
    out = []
    for s in SITES:
        try:
            stats = summarize(s)
        except RuntimeError as e:
            print(f"  ⚠ skipping {s['name']}: {e}")
            continue
        out.append({**s, **stats})
        print(f"{s['name']:<18} {s['region']:<15} fog {stats['annual_pct']:>5}% of hours")
    if not out:
        raise SystemExit("no sites fetched; Open-Meteo unreachable?")
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
