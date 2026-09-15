# Moon Mission Data

Runtime data/assets for `kvsankar/moon-mission` deployments.

## Contents

- Orbit runtime artifacts under `assets/*/data/`:
  - `*.npz`
  - `*-cheb.json`
  - `*-cheb.json.gz`
  - `*-meta.json`
  - `*-style.json`
  - `ephemeris-manifest.json`
- Shared render textures under `images/`
- Vendored runtime libraries under `third-party/`
- Mission screenshots under `assets/*/images/`

## Runtime-Only Policy

This repository is intentionally pruned to keep only files required by the current `moon-mission` runtime.

- Source-of-truth for runtime requirements is the app repo (`../moon-mission`):
  - Mission manifests: `assets/*/data/ephemeris-manifest.json`
  - Relative-mode and orbit-style file conventions from mission `config.json`
  - Shared texture references from platform `texture-loader.js` and `moon-render-asset-profiles.js`
  - Third-party references from `mission.html` and platform imports
- Unused tracked files should be removed.

## Physical Moon assets

Data `main` supplies the runtime assets for the completed Physical Moon renderer
on app `master`. All six profile assets are available for staging. High retains
its accepted source data; the 4K/16K color and precise High height files remain
byte-identical to their app copies.

| Tier | Color under `images/moon/` | Terrain under `images/moon/` |
| --- | --- | --- |
| Low | `lroc_color_2025_2k_low.jpg` | `terrain-low-v2.moon.gz` |
| Medium | `lroc_color_2025_4k_fast.jpg` | `terrain-medium-v2.moon.gz` |
| High | `lroc_color_2025_16k_quality.jpg` | `ldem_16_uint_quality.png` |

Low/Medium V2 packages preserve the V1 height samples byte-for-byte and contain
RGB8 normals filtered from native-resolution physical slopes. GPU dimensions stay
unchanged; the extra downloads are 98,011 bytes (Low) and 272,763 bytes (Medium).
Keep V1 files for existing app consumers until their rollout is retired. High's
assets and rendering settings are unchanged. [Terrain provenance](images/moon/terrain-v2-provenance.json)
records the source hash, reduction, dimensions, format and package hashes.
The Low color is a 2K Pillow Lanczos resize of the existing 4K color, JPEG quality
85; its SHA-256 is `55152d79d98eec8af51e4b7a32f9f1e9d7a82eaec162644842d4f4adbef98261`.

Generate these files in the app repository with `scripts/generate-moon-preview.py`
and `scripts/generate-moon-terrain.mjs`, then mirror them here byte-for-byte.
The 1K preview and Sun-corona textures remain app-owned under `src/platform/assets/`.
See the app's [asset preparation guide](https://github.com/kvsankar/moon-mission/blob/master/docs/operations/data/moon-render-assets.md)
and [architecture](https://github.com/kvsankar/moon-mission/blob/master/docs/designs/rendering/moon-rendering.md).
Publish the new Low color and both packages at the production asset base before
deploying the consuming app. A branch push alone does not deploy them.

## Provenance and Audit

- Provenance docs live under [`provenance/`](provenance/README.md).
- Machine-readable audit manifest:
  - `provenance/runtime-asset-manifest.json`
- Generator script:
  - `scripts/generate_runtime_asset_manifest.py`

Regenerate:

```bash
python scripts/generate_runtime_asset_manifest.py --app-root ../moon-mission
```

Regenerate NASA 2020 sky textures (stars map + constellation figures):

```bash
python scripts/update_sky_textures_from_nasa.py --data-root .
```

Prune tracked files not required by runtime:

```bash
python scripts/generate_runtime_asset_manifest.py --app-root ../moon-mission --prune-unused
```
