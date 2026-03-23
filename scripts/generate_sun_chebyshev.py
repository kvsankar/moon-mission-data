#!/usr/bin/env python3
"""
Generate Sun-only Chebyshev ephemeris artifacts from mission NPZ files.

This script is intended for moon-mission-data. It reads each mission
`ephemeris-manifest.json`, derives SUN vectors from phase NPZ artifacts, writes
`*-sun-cheb.json` (+ `.gz`) runtime files, and updates the manifest with a
`sun_chebyshev` artifact entry.
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def load_compressor_module(app_root: Path):
    scripts_dir = app_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    module_path = app_root / "scripts" / "compress-orbits.py"
    if not module_path.exists():
        raise FileNotFoundError(f"compress-orbits.py not found at: {module_path}")

    spec = importlib.util.spec_from_file_location("compress_orbits", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import compressor module from: {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compute_velocity_from_positions(jd: np.ndarray, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(jd)
    vx = np.zeros(n, dtype=float)
    vy = np.zeros(n, dtype=float)
    vz = np.zeros(n, dtype=float)

    if n < 2:
        return vx, vy, vz

    for i in range(1, n - 1):
        dt_seconds = float(jd[i + 1] - jd[i - 1]) * 86400.0
        if dt_seconds == 0:
            continue
        vx[i] = float(x[i + 1] - x[i - 1]) / dt_seconds
        vy[i] = float(y[i + 1] - y[i - 1]) / dt_seconds
        vz[i] = float(z[i + 1] - z[i - 1]) / dt_seconds

    dt0_seconds = float(jd[1] - jd[0]) * 86400.0
    if dt0_seconds != 0:
        vx[0] = float(x[1] - x[0]) / dt0_seconds
        vy[0] = float(y[1] - y[0]) / dt0_seconds
        vz[0] = float(z[1] - z[0]) / dt0_seconds

    dtn_seconds = float(jd[-1] - jd[-2]) * 86400.0
    if dtn_seconds != 0:
        vx[-1] = float(x[-1] - x[-2]) / dtn_seconds
        vy[-1] = float(y[-1] - y[-2]) / dtn_seconds
        vz[-1] = float(z[-1] - z[-2]) / dtn_seconds

    return vx, vy, vz


def load_sun_npz_data(npz_path: Path) -> dict[str, np.ndarray]:
    with np.load(npz_path) as npz:
        if "SUN_vectors" not in npz:
            raise KeyError("SUN_vectors")
        sun = npz["SUN_vectors"]

    jd = sun["jdct"].astype(float)
    x = sun["x"].astype(float)
    y = sun["y"].astype(float)
    z = sun["z"].astype(float)
    vx, vy, vz = compute_velocity_from_positions(jd, x, y, z)

    return {
        "jd": jd,
        "x": x,
        "y": y,
        "z": z,
        "vx": vx,
        "vy": vy,
        "vz": vz,
    }


def to_assets_generated_path(*, mission: str, filename: str) -> str:
    return (Path("assets") / mission / "data" / filename).as_posix()


def write_gzip_copy(json_path: Path) -> Path:
    gzip_path = json_path.with_name(f"{json_path.name}.gz")
    payload = json_path.read_bytes()
    gzip_path.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
    return gzip_path


def process_manifest(*, manifest_path: Path, data_root: Path, compressor_module, phases_filter: set[str] | None) -> dict[str, int]:
    manifest = read_json(manifest_path)
    mission_name = manifest.get("mission")
    if not isinstance(mission_name, str) or not mission_name:
        raise ValueError(f"Manifest missing mission name: {manifest_path}")

    phases = manifest.get("phases", {})
    if not isinstance(phases, dict):
        raise ValueError(f"Manifest phases must be an object: {manifest_path}")

    changed_manifest = False
    generated_count = 0
    skipped_no_sun = 0
    skipped_missing_npz = 0

    for phase_name, phase_cfg in phases.items():
        if phases_filter and phase_name not in phases_filter:
            continue
        if not isinstance(phase_cfg, dict):
            continue

        artifacts = phase_cfg.get("artifacts", {})
        if not isinstance(artifacts, dict):
            continue

        npz_artifact = artifacts.get("npz", {})
        npz_runtime = npz_artifact.get("runtime") if isinstance(npz_artifact, dict) else None
        if not isinstance(npz_runtime, str) or not npz_runtime:
            continue

        npz_path = manifest_path.parent / npz_runtime
        if not npz_path.exists():
            skipped_missing_npz += 1
            print(f"[skip:{mission_name}:{phase_name}] NPZ missing: {npz_path}")
            continue

        try:
            npz_data = load_sun_npz_data(npz_path)
        except KeyError:
            skipped_no_sun += 1
            print(f"[skip:{mission_name}:{phase_name}] NPZ has no SUN_vectors: {npz_path.name}")
            continue

        base_name = Path(npz_runtime).stem
        sun_cheb_name = f"{base_name}-sun-cheb.json"
        sun_cheb_path = manifest_path.parent / sun_cheb_name
        tolerance_km = float(phase_cfg.get("tolerance_km", 5))

        print(f"[gen:{mission_name}:{phase_name}] {sun_cheb_name} (tol={tolerance_km:g} km)")
        segments = compressor_module.compress_orbit_data_tolerance(
            npz_data,
            tolerance_km=tolerance_km,
        )

        payload = {
            "format": "chebyshev-ephemeris",
            "version": "1.0",
            "metadata": {
                "source": npz_runtime,
                "body": "SUN",
                "created": datetime.now(timezone.utc).isoformat(),
                "tolerance_km": tolerance_km,
                "segments_count": len(segments),
                "coordinate_frame": "J2000",
                "units": {
                    "time": "julian_date",
                    "position": "km",
                },
            },
            "time_range": {
                "start": float(npz_data["jd"][0]),
                "end": float(npz_data["jd"][-1]),
            },
            "segments": segments,
        }
        write_json(sun_cheb_path, payload)
        write_gzip_copy(sun_cheb_path)
        generated_count += 1

        generated_ref = to_assets_generated_path(
            mission=mission_name,
            filename=sun_cheb_name,
        )
        existing_sun = artifacts.get("sun_chebyshev")
        next_sun = {
            "runtime": sun_cheb_name,
            "generated": generated_ref,
        }
        if existing_sun != next_sun:
            artifacts["sun_chebyshev"] = next_sun
            phase_cfg["artifacts"] = artifacts
            phases[phase_name] = phase_cfg
            changed_manifest = True

    if changed_manifest:
        manifest["phases"] = phases
        write_json(manifest_path, manifest)

    return {
        "generated_count": generated_count,
        "skipped_no_sun": skipped_no_sun,
        "skipped_missing_npz": skipped_missing_npz,
        "manifest_updated": 1 if changed_manifest else 0,
    }


def discover_manifests(data_root: Path, missions_filter: set[str] | None) -> list[Path]:
    manifests = sorted(data_root.glob("assets/*/data/ephemeris-manifest.json"))
    if not missions_filter:
        return manifests

    filtered = []
    for path in manifests:
        mission = path.parent.parent.name
        if mission in missions_filter:
            filtered.append(path)
    return filtered


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Sun Chebyshev artifacts from mission NPZ files")
    parser.add_argument(
        "--data-root",
        default=".",
        help="Path to moon-mission-data repository root (default: .)",
    )
    parser.add_argument(
        "--app-root",
        default="../moon-mission",
        help="Path to moon-mission app repository for compressor import (default: ../moon-mission)",
    )
    parser.add_argument(
        "--missions",
        nargs="+",
        default=None,
        help="Optional mission ids (e.g., chandrayaan3 apollo10-lm). Defaults to all.",
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        default=["geo", "lunar"],
        help="Phase keys to process (default: geo lunar).",
    )
    args = parser.parse_args()

    data_root = Path(args.data_root).resolve()
    app_root = Path(args.app_root).resolve()
    missions_filter = set(args.missions) if args.missions else None
    phases_filter = set(args.phases) if args.phases else None

    compressor_module = load_compressor_module(app_root)
    manifests = discover_manifests(data_root, missions_filter)
    if not manifests:
        print("No ephemeris manifests found for the requested scope.")
        return 1

    totals = {
        "generated_count": 0,
        "skipped_no_sun": 0,
        "skipped_missing_npz": 0,
        "manifest_updated": 0,
    }

    for manifest_path in manifests:
        stats = process_manifest(
            manifest_path=manifest_path,
            data_root=data_root,
            compressor_module=compressor_module,
            phases_filter=phases_filter,
        )
        for key in totals:
            totals[key] += stats.get(key, 0)

    print("\nSun Chebyshev generation summary")
    print("--------------------------------")
    print(f"Manifests scanned: {len(manifests)}")
    print(f"Artifacts generated: {totals['generated_count']}")
    print(f"Manifests updated: {totals['manifest_updated']}")
    print(f"Skipped (no SUN_vectors): {totals['skipped_no_sun']}")
    print(f"Skipped (missing NPZ): {totals['skipped_missing_npz']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
