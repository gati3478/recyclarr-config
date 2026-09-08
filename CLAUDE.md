# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Recyclarr configuration for a Direct Play-only Plex setup on a Whatbox seedbox. No source code, no build system — just YAML configs that `recyclarr sync` pushes to Radarr and Sonarr.

## Files

- `recyclarr.yml` — the live config with the real ports, **a symlink** into the dotfiles repo: `../dotfiles/private/whatbox/files/recyclarr/recyclarr.yml`, the copy that repo deploys to the box and versions. One file with two names since 09-09-2026: an edit here is the deploy source at once, and `whatbox-pull` writes the box's version back into it. Gitignored here — this repo is public and the ports are the seedbox's — so a fresh clone has no `recyclarr.yml` until the link is made:

  ```
  ln -s ../dotfiles/private/whatbox/files/recyclarr/recyclarr.yml recyclarr.yml
  ```

  It carries **no credential**: the two `api_key` lines are `!secret radarr_api_key` / `!secret sonarr_api_key`, resolved on the box from `~/.config/recyclarr/secrets.yml`, which exists only there. ⚠️ Claude Code's Edit tool refuses to write through a symlink — in a session, edit the target path in the dotfiles repo; every other editor follows the link.
- `recyclarr-template.yml` — the shareable version, identical except for two placeholders (`RADARR_PORT`, `SONARR_PORT`)

Both files carry a `yaml-language-server` schema header pointing at recyclarr's config schema, so schema-aware editors validate structure on save.

## Syncing and deploying

Recyclarr is not installed on this machine, and `sync` reaches Radarr and Sonarr only from the box, so the deploy goes through the dotfiles repo — which governs the box's copy at `~/.config/recyclarr/recyclarr.yml` as a manifest row — and every check runs on the box. **Never `scp` straight onto the box**: `dot-doctor` would report drift, and `whatbox-apply` would put the governed copy back.

```
~/Development/dotfiles/private/bin/whatbox-apply     # deploys the edited file, re-checks
ssh whatbox '~/bin/recyclarr sync --preview'          # the parse and the diff, against today's guide
ssh whatbox '~/bin/recyclarr sync'                    # or wait for Monday 04:00 UTC
```

`--preview` exits 0 on a config parse error — read its output, not its exit code. The binary is `~/bin/recyclarr` on the box (a pinned `promises.tsv` row), not on the default non-interactive PATH. A Docker form of the preview used to live here; retired 09-09-2026 — it validated parsing only, needed a dummy `secrets.yml` mounted to parse at all, and the `latest` tag it named no longer exists.

No other commands exist. There are no tests, no linting, no build steps.

## Template parity (doctor-asserted)

`recyclarr.yml` and `recyclarr-template.yml` must stay identical except for the two `base_url` lines:

```
diff recyclarr.yml recyclarr-template.yml    # exactly 2 differing lines, both base_url
```

`dot-doctor` in the dotfiles repo asserts this on every run, and that `recyclarr.yml` here is the link. Edit `recyclarr.yml` first, then regenerate the template from it — never hand-edit the template into drift:

```
awk '/^radarr:/{s="RADARR"} /^sonarr:/{s="SONARR"} {sub(/localhost:[0-9]+/, "localhost:" s "_PORT"); print}' recyclarr.yml > recyclarr-template.yml
```

(A PostToolUse hook used to claim this job. It was scoped to a mistyped path and never fired, and its rule of four differing lines had been two since the `!secret` split; retired 09-09-2026.)

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
- Change `recyclarr.yml` first, then regenerate `recyclarr-template.yml` from it with the `awk` line under Template parity. The doctor warns until they match.
- Every `trash_id` entry has an inline comment with the format's exact guide name (e.g., `# DTS-HD MA`). Keep comments verbatim-identical to the TRaSH guide `name` field so they can be verified mechanically against the guide JSON (`docs/json/{radarr,sonarr}/cf/*.json` in the TRaSH-Guides repo).
- Scores assigned to profiles within the same `assign_scores_to` block typically share the same value across profiles unless there's a specific reason to differ (e.g., LQ is `-2500` for HD but `-4500` for UHD — UHD junk costs more disk and lives longer, so it's penalized harder).
