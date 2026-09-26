"""Fog / low-cloud frequency from MODIS Terra morning passes (Google Earth Engine).

First-pass proxy: fraction of clear-sky-or-cloudy daily observations flagged
"cloudy" in MOD09GA state_1km (bits 0-1). Terra crosses around 10:30 local
time, when coastal fog is often still on the ground. High cloud gets mixed
in; separating it out is a later step.

Set EE_PROJECT to your Earth Engine cloud project.
"""
import os

import ee

AOIS = {
    "namib":      [14.3, -23.5, 15.2, -22.3],   # Gobabeb / Walvis Bay fog belt
    "atacama":    [-70.3, -20.9, -69.9, -20.2],  # Alto Patache fog oasis
    "california": [-123.2, 37.4, -122.3, 38.2],  # Golden Gate / Marin coast
}
START, END = "2025-01-01", "2026-01-01"


def cloudy(img):
    state = img.select("state_1km")
    cs = state.bitwiseAnd(3)            # 0 clear, 1 cloudy, 2 mixed, 3 not set
    valid = cs.lte(2)
    return cs.eq(1).rename("cloudy").updateMask(valid).copyProperties(img, ["system:time_start"])


def monthly_frequency(bbox):
    geom = ee.Geometry.Rectangle(bbox)
    col = ee.ImageCollection("MODIS/061/MOD09GA").filterDate(START, END).filterBounds(geom).map(cloudy)

    def month(m):
        m = ee.Number(m)
        sub = col.filter(ee.Filter.calendarRange(m, m, "month"))
        return sub.mean().multiply(100).rename("fog_pct").set("month", m).clip(geom)

    return ee.ImageCollection(ee.List.sequence(1, 12).map(month)), geom


def main() -> None:
    ee.Initialize(project=os.environ.get("EE_PROJECT"))
    for name, bbox in AOIS.items():
        monthly, geom = monthly_frequency(bbox)
        stats = monthly.map(lambda im: ee.Feature(None, {
            "month": im.get("month"),
            "mean_fog_pct": im.reduceRegion(ee.Reducer.mean(), geom, 1000).get("fog_pct"),
        }))
        rows = stats.aggregate_array("mean_fog_pct").getInfo()
        print(f"{name:<11} " + " ".join(f"{(v or 0):5.1f}" for v in rows))


if __name__ == "__main__":
    main()
