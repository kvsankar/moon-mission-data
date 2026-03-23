# Moon Mission Data

Runtime data/assets for `kvsankar/moon-mission` deployments.

## Contents

- Orbit runtime artifacts under `assets/*/data/`:
  - `*.npz`
  - `*-cheb.json`
  - `*-cheb.json.gz`
  - `*-meta.json`
  - `ephemeris-manifest.json`
- Shared render textures under `images/`
- Vendored runtime libraries under `third-party/`
- Mission screenshots under `assets/*/images/`

## Runtime-Only Policy

This repository is intentionally pruned to keep only files required by the current `moon-mission` runtime.

- Source-of-truth for runtime requirements is the app repo (`../moon-mission`):
  - Mission manifests: `assets/*/data/ephemeris-manifest.json`
  - Relative-mode file conventions from mission `config.json`
  - Shared texture references from platform `texture-loader.js`
  - Third-party references from `mission.html` and platform imports
- Unused tracked files should be removed.

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

Prune tracked files not required by runtime:

```bash
python scripts/generate_runtime_asset_manifest.py --app-root ../moon-mission --prune-unused
```
