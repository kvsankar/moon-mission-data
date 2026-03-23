# Moon Mission Data

Runtime NPZ ephemeris artifacts for `kvsankar/moon-mission` deployments.

## Notes

- This repository stores deploy-time `.npz` files consumed by CI workflows.
- Source manifests are in the app repo under `assets/*/data/ephemeris-manifest.json`.
- Deployment pipelines stage these files into `dist-pages/assets/*/data/` before publish.
