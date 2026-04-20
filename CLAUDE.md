# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Recyclarr configuration for a Direct Play-only Plex setup on a Whatbox seedbox. No source code, no build system — just YAML configs that `recyclarr sync` pushes to Radarr and Sonarr.

## Files

- `recyclarr.yml` — Live config with real credentials and ports (deployed via `recyclarr sync`)
- `my-recyclarr-template-.yml` — Shareable version with placeholder credentials (`RADARR_API_KEY`, `SONARR_API_KEY`, etc.)

## Syncing

```
recyclarr sync --preview   # dry run — show diffs without pushing
recyclarr sync             # apply to Radarr/Sonarr
```

No other commands exist. There are no tests, no linting, no build steps.

## Verifying template parity

`recyclarr.yml` and `my-recyclarr-template-.yml` must stay structurally identical — only credentials differ:

```
diff recyclarr.yml my-recyclarr-template-.yml
```

Expected output: exactly 4 differing lines (the two `base_url` and two `api_key` lines — one pair for Radarr, one for Sonarr). Any other diff means the files have drifted and one needs updating.

## Hardware Constraints (These Drive All Scoring Decisions)

- **No transcoding**: Whatbox seedbox, Plex must Direct Play everything
- **No DTS**: Sonos Beam 2 cannot decode DTS; Plex can't transcode audio either. All DTS formats get `-10000`
- **No HDR10+**: LG C1 doesn't support it. HDR10+ Boost gets only `+100` (non-zero to act as tiebreaker, not a priority)
- **Dolby Vision needs HDR10 fallback**: DV without fallback gets `-10000` (C1 + Plex webOS requirement)
- **No Remux/BR-DISK**: Too large for seedbox storage, and Direct Play makes raw disc pointless

## Profile Architecture

### Radarr (2 profiles)

- **HD-Kino** (`sqp-1-1080p` base) — 1080p cap, ~6-16 GB
- **UHD-Kino** (`sqp-1-2160p` base) — up to 2160p, ~20-35 GB

Radarr's `score_set: sqp-1-*` pulls a TRaSH SQP baseline; our `custom_formats` block then overrides specific scores on top of that baseline.

### Sonarr (2 profiles)

- **HD** — 1080p cap, no score_set (all scoring via custom_formats)
- **UHD** — up to 2160p, no score_set

Sonarr has no baseline — `custom_formats` are the sole source of scoring. When debugging a Radarr release with a score you didn't explicitly assign, check the SQP baseline; in Sonarr that can't happen.

All profiles use `reset_unmatched_scores: true` so TRaSH base scores not explicitly overridden get zeroed out.

## Scoring Conventions

- `-10000` = hard block (DTS, Remux, BR-DISK, DV without fallback)
- `-2500` to `-4500` = strong penalty (LQ, Bad Dual Groups, Obfuscated)
- `-50` to `-1000` = soft penalty (Scene, Retags, No-RlsGroup, x265 without HDR)
- `+5` to `+7` = tiebreakers (Repack/Proper, Repack2, Repack3 — grab the corrected release when otherwise equal)
- `+10` to `+100` = light preference (10bit, x265 in UHD, HDR10+, generic HDR +50)
- `+450` to `+1350` = strong preference (DD/DD+/ATMOS audio hierarchy)
- `+1000` = major feature boost (DV Boost)

Audio scoring hierarchy (same across all profiles):
DD+ ATMOS (1350) > DD+/ATMOS undefined (1250) > TrueHD ATMOS (750) > TrueHD (650) > DD (450)

Audio scores are intentionally flat across HD and UHD — the Beam 2 doesn't care what resolution precedes it, so the same hierarchy applies everywhere.

TrueHD is scored positively despite Beam 2 incompatibility because releases with TrueHD always include a DD/AC3 fallback track.

HDR hierarchy (UHD profiles only): generic HDR (+50) stacks with DV Boost (+1000) and HDR10+ Boost (+100) to give DV+fallback ~+1050 > HDR10+ ~+150 > HDR10 +50 > SDR 0. DV without HDR10 fallback is blocked hard (-10000) regardless.

## Editing Guidelines

- Radarr and Sonarr use **different `trash_ids`** for the same format name. Never copy a trash_id between the radarr and sonarr sections.
- When changing a score, update it in **both** `recyclarr.yml` and `my-recyclarr-template-.yml` to keep them in sync. The only differences between the two files should be credentials/ports.
- Every `trash_id` entry should have an inline comment identifying the format (e.g., `# DTS-HD MA`).
- Scores assigned to profiles within the same `assign_scores_to` block typically share the same value across profiles unless there's a specific reason to differ (e.g., LQ is `-2500` for HD but `-4500` for UHD).
