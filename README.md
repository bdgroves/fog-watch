# 🌫️ FOG-WATCH

**Mapping where the fog lives, so we can find what lives in it.**

Fog isn't just weather. In 2026, Ferran Garcia-Pichel's team at Arizona State reported bacteria that live and feed inside fog droplets, with pigments that shield them from UV. If fog is a habitat, it needs a habitat map. FOG-WATCH builds a rolling fog-frequency heatmap for the world's great fog coasts from free satellite data and flags the foggiest, most reachable spots as candidate sampling sites.

**🌐 Live site: [brooksgroves.com/fog-watch](https://brooksgroves.com/fog-watch/)**

> Part of the GeoAI & Remote Sensing Lab · sibling of [ANOLE-WATCH](https://github.com/bdgroves/Anole-watch) and [ALPINE-WATCH](https://github.com/bdgroves/Alpine-watch)

---

## Status: 🌱 first data layer

| Piece | State |
|---|---|
| Fog climatology from ERA5 via Open-Meteo, no API key (`src/fog_climatology.py`) | ✅ written — run the **Fog climatology** Action |
| Landing page charts: Namib inland transect · hour × month heatmap · three coasts | ✅ built, read `docs/data/fog.json` |
| Monthly auto-refresh | ✅ wired |
| Satellite fog frequency, MODIS via Earth Engine (`src/fog_frequency.py`) | ✅ written, needs an Earth Engine project |
| True fog vs. high-cloud separation (GOES + DEM) | ⬜ later |
| Candidate sampling-site ranking | ⬜ later |

### Sites

- **Namib:** Walvis Bay, Swakopmund, Gobabeb (56 km inland), Sossusvlei, plus an 8-point transect due east from the coast at Gobabeb's latitude (11–153 km inland)
- **Atacama:** Alto Patache fog oasis
- **California:** Golden Gate

**Fog rule:** an hour is foggy when ERA5 low cloud ≥ 70% and 2 m relative humidity ≥ 95%. ERA5 is a ~25 km grid, so this is a regional signal. Tune both thresholds in `src/fog_climatology.py`.

## Data sources

- **ERA5 reanalysis** via [Open-Meteo](https://open-meteo.com) historical API (CC BY 4.0): hourly low cloud cover and humidity, 2016 on
- **MODIS Terra MOD09GA** (Earth Engine): morning cloud-state flags as a satellite fog proxy
- **GOES-18 ABI** low cloud & fog (later) · **Sentinel-2** NDVI · **Copernicus DEM**

## Run it

```bash
pixi install
pixi run climatology                          # writes docs/data/fog.json
pixi run serve                                # http://localhost:8000
EE_PROJECT=your-gee-project pixi run -e ee fog-satellite   # optional, needs `earthengine authenticate`
```

## Build prompt (for the next session)

> Help me build out FOG-WATCH. Run src/fog_frequency.py for the Namib, Atacama and California coast study areas and export monthly fog-frequency rasters. Then separate true fog and low stratus from high cloud using terrain (Copernicus DEM) and GOES-18 cloud-top height, and rank candidate field-sampling sites by fog frequency and road access. Display it as a Leaflet heatmap in the ALPINE-WATCH dark navy/teal style.
