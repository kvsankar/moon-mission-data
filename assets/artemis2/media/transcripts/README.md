# Artemis II Flyby Broadcast Transcripts

These files are generated transcript artifacts for the Artemis II lunar flyby broadcast. The app repo references them from `assets/artemis2/data/media-manifest.json5`.

Canonical runtime files:

- `artemis2-lunar-flyby-broadcast-combined.json`: unified Part 1 + Part 2 transcript timeline with speaker labels and word-level alignment.
- `artemis2-lunar-flyby-broadcast.index.json`: curated entity/search index built from the combined transcript.
- `artemis2-lunar-flyby-broadcast-part1.vtt`: Part 1 WebVTT fallback captions.
- `artemis2-lunar-flyby-broadcast-part2.vtt`: Part 2 WebVTT fallback captions.
- `artemis2-lunar-flyby-broadcast-part1.labels.yaml`: Part 1 speaker/provenance label sidecar.
- `artemis2-lunar-flyby-broadcast-part2.labels.yaml`: Part 2 speaker/provenance label sidecar.

Source and regeneration details are documented in:

- App repo: `docs/operations/artemis2-transcripts-complete-handoff.md`
- Transcription workspace: `C:\sankar\projects\transcribe`

The source `.webm` files and intermediate transcripts are local generation inputs and should not be committed here.
