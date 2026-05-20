# Artemis II Flyby Broadcast Transcripts

These files are generated transcript artifacts for the Artemis II lunar flyby broadcast. The app repo references them from `assets/artemis2/data/media-manifest.json5`.

Current source snapshot:

- Transcribe repo commit: `47615b1 Add reference transcript text repair`
- Repair stage: `repair_text_from_reference.py`
- Repair summary: 13 transcript slices repaired, 165.717 seconds of displayed transcript time repaired, 1 inserted missing cue, 2 orphan-tail merges, 10 prefix-loss repairs.

Canonical runtime files:

- `artemis2-lunar-flyby-broadcast-combined.json`: unified Part 1 + Part 2 transcript timeline with speaker labels, word-level alignment, and schema v4 `displayStartSeconds` / `displayEndSeconds` caption ranges.
- `artemis2-lunar-flyby-broadcast.index.json`: curated entity/search index built from the combined transcript. Mention `startSeconds` / `endSeconds` use display timing; raw segment lineage is kept as `segmentStartSeconds` / `segmentEndSeconds`.
- `artemis2-lunar-flyby-broadcast-part1.vtt`: Part 1 WebVTT fallback captions.
- `artemis2-lunar-flyby-broadcast-part2.vtt`: Part 2 WebVTT fallback captions.
- `artemis2-lunar-flyby-broadcast-part1.labels.yaml`: Part 1 speaker/provenance label sidecar.
- `artemis2-lunar-flyby-broadcast-part2.labels.yaml`: Part 2 speaker/provenance label sidecar.

Integration notes:

- Treat `artemis2-lunar-flyby-broadcast-combined.json` as the app-facing source of truth for transcript UI.
- Use `displayStartSeconds` / `displayEndSeconds` for captions, transcript highlighting, and seek targets.
- Treat `startSeconds` / `endSeconds` as provenance boundaries only.
- Some repaired segments intentionally have empty `words[]`; use segment-level display timing for those.

Source and regeneration details are documented in:

- App repo: `docs/operations/artemis2-transcripts-complete-handoff.md`
- Transcription workspace: `C:\sankar\projects\transcribe`

The source `.webm` files and intermediate transcripts are local generation inputs and should not be committed here.
