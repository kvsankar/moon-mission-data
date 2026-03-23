#!/usr/bin/env python3
"""
Generate a machine-readable runtime asset manifest for moon-mission-data.

The manifest is derived from the active moon-mission application repository:
  - Orbit artifacts declared in assets/*/data/ephemeris-manifest.json
  - Relative-mode Chebyshev files inferred from config.json spacecraft mnemonic
  - Mission image references from config.json mission_image
  - Shared texture references from platform texture-loader.js
  - Shared third-party references from mission.html and platform imports

This script can also prune tracked files that are not required by the app.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

THIRD_PARTY_PROVENANCE = {}


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_platform_file(app_root: Path, rel_path: str) -> Path:
    candidates = [
        app_root / "src" / "platform" / rel_path,
        app_root / "assets" / "platform" / rel_path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Unable to locate platform file {rel_path} in src/ or assets/")


def collect_required(app_root: Path) -> tuple[set[str], dict[str, str]]:
    required: set[str] = set()
    reasons: dict[str, str] = {}

    for manifest_path in sorted(app_root.glob("assets/*/data/ephemeris-manifest.json")):
        mission = manifest_path.parent.parent.name
        rel_manifest = (Path("assets") / mission / "data" / "ephemeris-manifest.json").as_posix()
        required.add(rel_manifest)
        reasons[rel_manifest] = "ephemeris-manifest"

        manifest = _read_json(manifest_path)
        phases = manifest.get("phases", {})
        has_landing_variants = isinstance(phases, dict) and (
            "landing-geo" in phases or "landing-lunar" in phases
        )
        if not isinstance(phases, dict):
            continue

        for phase, phase_cfg in phases.items():
            if not isinstance(phase_cfg, dict):
                continue
            if phase == "landing" and has_landing_variants:
                continue

            artifacts = phase_cfg.get("artifacts", {})
            if not isinstance(artifacts, dict):
                continue

            for key in ("npz", "chebyshev", "meta"):
                artifact_cfg = artifacts.get(key, {})
                if not isinstance(artifact_cfg, dict):
                    continue
                runtime_name = artifact_cfg.get("runtime")
                if not isinstance(runtime_name, str) or not runtime_name:
                    continue

                rel_path = (Path("assets") / mission / "data" / runtime_name).as_posix()
                required.add(rel_path)
                reasons[rel_path] = f"manifest:{mission}:{phase}:{key}"

                if runtime_name.endswith("-cheb.json"):
                    gz_path = (Path("assets") / mission / "data" / f"{runtime_name}.gz").as_posix()
                    required.add(gz_path)
                    reasons[gz_path] = f"manifest:{mission}:{phase}:chebyshev-gzip"

    # Relative mode assets are selected outside the manifest at runtime.
    for config_path in sorted(app_root.glob("assets/*/data/config.json")):
        mission = config_path.parent.parent.name
        config = _read_json(config_path)
        mnemonic = config.get("spacecraft_mnemonic")
        if isinstance(mnemonic, str) and mnemonic:
            rel_cheb = f"relative-{mnemonic}-cheb.json"
            rel_cheb_path = (Path("assets") / mission / "data" / rel_cheb).as_posix()
            rel_cheb_gz_path = (Path("assets") / mission / "data" / f"{rel_cheb}.gz").as_posix()
            required.add(rel_cheb_path)
            required.add(rel_cheb_gz_path)
            reasons[rel_cheb_path] = f"relative-mode:{mission}"
            reasons[rel_cheb_gz_path] = f"relative-mode:{mission}:gzip"

        mission_image = config.get("mission_image")
        if isinstance(mission_image, str) and mission_image:
            normalized = mission_image.replace("\\", "/")
            required.add(normalized)
            reasons[normalized] = f"config:mission_image:{mission}"

    texture_loader = _find_platform_file(app_root, "js/app/texture-loader.js")
    texture_text = texture_loader.read_text(encoding="utf-8")
    for match in re.finditer(r'"(images/[^"]+)"', texture_text):
        path = match.group(1)
        required.add(path)
        reasons[path] = "platform:texture-loader"

    mission_html = (app_root / "mission.html").read_text(encoding="utf-8")
    for match in re.finditer(r'"(third-party/[^"]+)"', mission_html):
        path = match.group(1)
        required.add(path)
        reasons[path] = "mission-html:script-tag"

    platform_root_candidates = [
        app_root / "src" / "platform" / "js",
        app_root / "assets" / "platform" / "js",
    ]
    for platform_root in platform_root_candidates:
        if not platform_root.exists():
            continue
        for js_path in platform_root.glob("**/*.js"):
            text = js_path.read_text(encoding="utf-8")
            for match in re.finditer(r"""['"](?:\.\./)+((?:third-party|images)/[^'"]+)['"]""", text):
                path = match.group(1)
                required.add(path)
                reasons[path] = f"platform-import:{js_path.relative_to(app_root).as_posix()}"

    return required, reasons


def classify_path(path: str) -> str:
    if path.startswith("assets/") and "/data/" in path:
        return "orbit-artifact"
    if path.startswith("assets/") and "/images/" in path:
        return "mission-image"
    if path.startswith("images/"):
        return "shared-image"
    if path.startswith("third-party/"):
        return "third-party"
    return "other"


def build_entry(path: str, full_path: Path, reason: str) -> dict:
    category = classify_path(path)
    exists = full_path.exists()

    entry = {
        "path": path,
        "category": category,
        "reason": reason,
        "exists": exists,
    }
    if exists and full_path.is_file():
        entry["size_bytes"] = full_path.stat().st_size
        entry["sha256"] = _sha256(full_path)

    if category == "orbit-artifact":
        entry["provenance"] = {
            "status": "documented",
            "source": "Generated from JPL HORIZONS exports via moon-mission scripts/orbits.py and scripts/compress-orbits.py",
        }
    elif category == "third-party":
        entry["provenance"] = THIRD_PARTY_PROVENANCE.get(
            path,
            {
                "status": "legacy-unverified",
                "source": "Vendored runtime dependency; upstream metadata not yet cataloged.",
            },
        )
    else:
        entry["provenance"] = {
            "status": "legacy-unverified",
            "source": "Legacy media migrated from moon-mission; upstream attribution source pending full audit.",
        }

    return entry


def git(args: list[str], cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate runtime asset manifest for moon-mission-data")
    parser.add_argument(
        "--app-root",
        default="../moon-mission",
        help="Path to moon-mission application repository (default: ../moon-mission)",
    )
    parser.add_argument(
        "--data-root",
        default=".",
        help="Path to moon-mission-data repository root (default: .)",
    )
    parser.add_argument(
        "--output",
        default="provenance/runtime-asset-manifest.json",
        help="Path to output manifest JSON (default: provenance/runtime-asset-manifest.json)",
    )
    parser.add_argument(
        "--prune-unused",
        action="store_true",
        help="Delete tracked files that are not required by the app (via git rm).",
    )
    args = parser.parse_args()

    data_root = Path(args.data_root).resolve()
    app_root = Path(args.app_root).resolve()
    output_path = (data_root / args.output).resolve()

    required, reasons = collect_required(app_root)

    tracked_paths = git(["ls-files"], cwd=data_root).splitlines()
    tracked_set = set(tracked_paths)
    required_sorted = sorted(required)
    missing = sorted(path for path in required if path not in tracked_set)
    allowed_non_runtime_files = {"README.md"}
    allowed_non_runtime_prefixes = ("provenance/", "scripts/")
    unused = sorted(
        path
        for path in tracked_set
        if path not in required
        and path not in allowed_non_runtime_files
        and not path.startswith(allowed_non_runtime_prefixes)
    )

    if args.prune_unused and unused:
        subprocess.check_call(["git", "rm", "--", *unused], cwd=data_root)

    entries = []
    for path in required_sorted:
        entries.append(build_entry(path, data_root / path, reasons.get(path, "unknown")))

    payload = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "app_repo": {
            "path": app_root.as_posix(),
            "git_commit": git(["rev-parse", "HEAD"], cwd=app_root),
            "git_branch": git(["branch", "--show-current"], cwd=app_root),
        },
        "data_repo": {
            "path": data_root.as_posix(),
            "git_commit": git(["rev-parse", "HEAD"], cwd=data_root),
            "git_branch": git(["branch", "--show-current"], cwd=data_root),
        },
        "counts": {
            "required_paths": len(required_sorted),
            "tracked_paths": len(tracked_set),
            "missing_required": len(missing),
            "unused_tracked": len(unused),
        },
        "missing_required": missing,
        "unused_tracked": unused,
        "required_assets": entries,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")

    print(f"Wrote runtime asset manifest: {output_path.as_posix()}")
    print(f"Required: {len(required_sorted)}  Missing: {len(missing)}  Unused tracked: {len(unused)}")
    if missing:
        print("Missing required paths:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
