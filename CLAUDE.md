# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Recyclarr configuration for a Direct Play-only Plex setup on a Whatbox seedbox. No source code, no build system — just YAML configs that `recyclarr sync` pushes to Radarr and Sonarr.

## Files

- `recyclarr.yml` — Live config with real credentials and ports (gitignored; deployed via `recyclarr sync`)
- `recyclarr-template.yml` — Shareable version, identical except for four placeholders (`RADARR_PORT`, `RADARR_API_KEY`, `SONARR_PORT`, `SONARR_API_KEY`)

Both files carry a `yaml-language-server` schema header pointing at recyclarr's config schema, so schema-aware editors validate structure on save.

## Syncing

```
recyclarr sync --preview   # dry run — show diffs without pushing
recyclarr sync             # apply to Radarr/Sonarr
```

Recyclarr is not installed on this machine; run it via Docker when needed. Mount the repo read-only at `/repo` (not at `/config`, recyclarr's app-data dir — that scaffolds `configs/`, `logs/`, `state/` etc. into the repo) and point `-c` at the config; scaffolding then stays inside the disposable container:

```
docker run --rm -v "$PWD:/repo:ro" ghcr.io/recyclarr/recyclarr:latest sync --preview -c /repo/recyclarr.yml
```

No other commands exist. There are no tests, no linting, no build steps.

## Deploying to the Seedbox

Recyclarr runs on the whatbox itself — binary at `~/bin/recyclarr` (not on the default non-interactive PATH), config at `~/.config/recyclarr/recyclarr.yml`, SSH alias `whatbox`:

```
scp recyclarr.yml whatbox:.config/recyclarr/recyclarr.yml
ssh whatbox '~/bin/recyclarr sync --preview'   # inspect the diff first
ssh whatbox '~/bin/recyclarr sync'
```

## Template Parity (Hook-Enforced)

`recyclarr.yml` and `recyclarr-template.yml` must stay identical except credentials:

```
diff recyclarr.yml recyclarr-template.yml
```

Expected output: exactly 4 differing lines (the two `base_url` and two `api_key` lines — one pair for Radarr, one for Sonarr). A PostToolUse hook (`~/.claude/hooks/recyclarr-validate.sh`) enforces this after every Write/Edit to either file, so editing one raises a blocking error until the other matches. Edit `recyclarr.yml` first, then regenerate the template from it by substituting the four credential values — never hand-edit the template into drift.

## Hardware Constraints (These Drive All Scoring Decisions)

- **No transcoding**: Whatbox seedbox, Plex must Direct Play everything
- **No DTS**: Sonos Beam 2 cannot decode DTS; Plex can't transcode audio either. All DTS formats get `-10000`
- **No HDR10+**: LG C1 doesn't support it. HDR10+ Boost gets only `+100` (non-zero to act as tiebreaker, not a priority)
- **Dolby Vision needs HDR10 fallback**: DV without fallback gets `-10000` (C1 + Plex webOS requirement)
- **No Remux/BR-DISK**: Too large for seedbox storage, and Direct Play makes raw disc pointless

## Profile Architecture

Two profiles per service, one per resolution tier:

| Service | Profile  | Upgrade until | Size envelope |
| ------- | -------- | ------------- | ------------- |
| Radarr  | HD-Kino  | Bluray-1080p  | ~6–16 GB      |
| Radarr  | UHD-Kino | Bluray-2160p  | ~20–35 GB     |
| Sonarr  | HD       | Bluray-1080p  | per-episode   |
| Sonarr  | UHD      | Bluray-2160p  | per-episode   |

**There is no TRaSH baseline anywhere.** Neither service uses `score_set` or guide-profile `trash_id`s — the explicit `custom_formats` blocks are the entire scoring model, and every score a release can receive is visible in the YAML. (Recyclarr's `score_set` only selects which preset score applies to CFs listed _without_ an explicit `score:`; it never pulls formats in by itself. An earlier revision of this config carried inert `score_set: sqp-1-*` lines under that misunderstanding — they were removed as a no-op.)

HQ release-group scoring therefore comes from explicitly listed tier CFs in both services — Radarr: `HD Bluray Tier 01–03`, `UHD Bluray Tier 01–03`, `WEB Tier 01–03`; Sonarr: `HD Bluray Tier 01–02`, `WEB Tier 01–03` (TRaSH publishes no Sonarr UHD Bluray tiers). HD Bluray tiers are also assigned to the UHD profiles, which fall back to Bluray-1080p when no 2160p release exists.

All profiles use `reset_unmatched_scores: true`, so any format score not explicitly assigned by this config gets zeroed in the *arr instance.

## Scoring Conventions

- `-10000` = hard block (DTS, Remux, BR-DISK, DV without fallback)
- `-2500` to `-4500` = strong penalty (LQ, Bad Dual Groups, Obfuscated)
- `-50` to `-1000` = soft penalty (Scene, Retags, No-RlsGroup, x265 without HDR, Theatrical Cut)
- `+5` to `+7` = tiebreakers (Repack/Proper, Repack2, Repack3 — grab the corrected release when otherwise equal)
- `+10` to `+100` = light preference (10bit, x265 in UHD, HDR10+, generic HDR +50)
- `+75` to `+200` = HQ release-group tiers (both services). Scaled down from TRaSH defaults (1600–1800) so audio/HDR scoring still dominates. Bluray tiers sit slightly above WEB tiers (200/150/100 vs 175/125/75), mirroring TRaSH's ordering.
- `+25` to `+800` = movie versions (Radarr): IMAX / IMAX Enhanced +800, Hybrid +500 UHD / +100 HD, Open Matte +350, Criterion / Special Edition +150, Remaster and 4K Remaster +25–125 depending on profile. Sonarr scores Hybrid identically. Theatrical Cut is the one negative version (`-50`).
- `+450` to `+1350` = strong preference (DD/DD+/ATMOS audio hierarchy)
- `+1000` = major feature boost (DV Boost)

Audio scoring hierarchy (same across all profiles):
DD+ ATMOS (1350) > DD+/ATMOS undefined (1250) > TrueHD ATMOS (750) > TrueHD (650) > DD (450)

Audio scores are intentionally flat across HD and UHD — the Beam 2 doesn't care what resolution precedes it, so the same hierarchy applies everywhere.

TrueHD is scored positively despite Beam 2 incompatibility because releases with TrueHD always include a DD/AC3 fallback track.

HDR hierarchy (UHD profiles only): generic HDR (+50) stacks with DV Boost (+1000) and HDR10+ Boost (+100) to give DV+fallback ~+1050 > HDR10+ ~+150 > HDR10 +50 > SDR 0. DV without HDR10 fallback is blocked hard (-10000) regardless.

## Editing Guidelines

- Radarr and Sonarr use **different `trash_ids`** for the same format name. Never copy a trash_id between the radarr and sonarr sections.
- Change `recyclarr.yml` first, then regenerate `recyclarr-template.yml` from it (substituting the four credential values). The parity hook blocks anything else.
- Every `trash_id` entry has an inline comment with the format's exact guide name (e.g., `# DTS-HD MA`). Keep comments verbatim-identical to the TRaSH guide `name` field so they can be verified mechanically against the guide JSON (`docs/json/{radarr,sonarr}/cf/*.json` in the TRaSH-Guides repo).
- Scores assigned to profiles within the same `assign_scores_to` block typically share the same value across profiles unless there's a specific reason to differ (e.g., LQ is `-2500` for HD but `-4500` for UHD — UHD junk costs more disk and lives longer, so it's penalized harder).
