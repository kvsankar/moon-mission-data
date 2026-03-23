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

## Notes

- The app repository remains the source of platform code and mission configs.
- CI workflows stage these runtime assets from this repository before tests/deploy.
- Required orbit files are declared by mission manifests in the app repo:
  `assets/*/data/ephemeris-manifest.json`.
