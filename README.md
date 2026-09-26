# 🌫️ FOG-WATCH

**Mapping where the fog lives, so we can find what lives in it.**

Fog isn't just weather. In 2026, Ferran Garcia-Pichel's team at Arizona State reported bacteria that live and feed inside fog droplets, with pigments that shield them from UV. If fog is a habitat, it needs a habitat map. FOG-WATCH builds a rolling fog-frequency heatmap for the world's great fog coasts from free satellite data and flags the foggiest, most reachable spots as candidate sampling sites.

> Part of the GeoAI & Remote Sensing Lab · sibling of [ANOLE-WATCH](https://github.com/bdgroves/Anole-watch) and [ALPINE-WATCH](https://github.com/bdgroves/Alpine-watch)

---

## Status: 🌱 scaffold

| Piece | State |
|---|---|
| Earth Engine fog-frequency script (`src/fog_frequency.py`) | ✅ written, needs an Earth Engine project to run |
| Landing page (`docs/index.html`) | ✅ placeholder |
| Export monthly rasters for Namib · Atacama · California coast | ⬜ next |
| True fog vs. high-cloud separation (GOES + DEM) | ⬜ later |
| Candidate sampling-site ranking | ⬜ later |

## Data sources

- **MODIS Terra MOD09GA** (Earth Engine): morning cloud-state flags as a first fog / low-cloud proxy
- **GOES-18 ABI** low-cloud & fog product (later): sub-hourly coverage for the California coast
- **Sentinel-2** NDVI / land cover · **SRTM / Copernicus DEM** terrain

## Run it

```bash
pixi install
earthengine authenticate          # one time
EE_PROJECT=your-gee-project pixi run fog
```

## Build prompt (for the next session)

> Help me build out FOG-WATCH. Run src/fog_frequency.py for the Namib, Atacama and California coast study areas and export monthly fog-frequency rasters. Then separate true fog and low stratus from high cloud using terrain (Copernicus DEM) and GOES-18 cloud-top height, and rank candidate field-sampling sites by fog frequency and road access. Display it as a Leaflet heatmap in the ALPINE-WATCH dark navy/teal style.
