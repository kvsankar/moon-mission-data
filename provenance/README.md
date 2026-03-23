# Provenance Records

This directory contains reproducible provenance records for files retained in `moon-mission-data`.

## Files

- `runtime-asset-manifest.json`
  - Generated artifact listing every runtime file required by the current `moon-mission` app.
  - Includes category, reason-for-retention, existence checks, and SHA-256 hash for each required file.
  - Includes `missing_required` and `unused_tracked` lists for audit.

## Regeneration

From this repository root:

```bash
python scripts/generate_runtime_asset_manifest.py --app-root ../moon-mission
```

To also prune tracked files that are not required by the app:

```bash
python scripts/generate_runtime_asset_manifest.py --app-root ../moon-mission --prune-unused
```

## Provenance Status Semantics

- `documented`: origin and upstream/tooling source are recorded.
- `legacy-unverified`: file is required by runtime, but upstream attribution and/or acquisition details need explicit follow-up audit.
