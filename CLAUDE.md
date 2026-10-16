# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Recyclarr configuration for a Direct Play-only Plex setup on a Whatbox seedbox. No source code, no build system — one YAML file that `recyclarr sync` pushes to Radarr and Sonarr.

## Files

- `recyclarr.yml` — the live config, versioned here. It names no port and no key: `base_url` and `api_key` are `!secret radarr_url` / `!secret radarr_api_key` and the Sonarr pair, resolved on the box from `~/.config/recyclarr/secrets.yml`, which exists only there. plumage deploys it through a link — `~/Development/plumage/hosts/whatbox/files/recyclarr/recyclarr.yml` → `../../../../../recyclarr/recyclarr.yml` — so a plumage clone needs this repo cloned beside it.
- `README.md` — the public design write-up.
- `.githooks/pre-commit` — the publishing guard (below).
- `tests/` — the scoring battery: `releases.tsv` holds release titles and what each profile must do with them; `scores` checks them on the box.

The file carries a `yaml-language-server` schema header, so schema-aware editors validate it on save.

## Syncing and deploying

Recyclarr is not installed on this machine, and `sync` reaches Radarr and Sonarr only from the box, so every deploy goes through plumage and every check runs on the box:

```
~/Development/plumage/hosts/whatbox/bin/whatbox-apply   # deploys the edited file, re-checks
ssh -tt whatbox '~/bin/recyclarr sync --preview'        # the parse and the diff, against today's guide
ssh whatbox '~/bin/recyclarr-sync; tail -n 20 ~/.local/state/recyclarr/sync.log'   # the sync and its log, or wait for cron: Monday 04:00 UTC
tests/scores                                            # after the sync: release titles scored by the *arrs' own matcher
```

- **Never `scp` straight onto the box**: `preen doctor` reports the drift, and `whatbox-apply` puts the governed copy back.
- **The preview needs a PTY.** Its diff renders only to a terminal; `-tt` forces one even when stdin is not a terminal, as in a Claude Code session (one `-t` does not). Without it the preview prints log lines and no diff, which reads as clean. It also exits 0 on a parse error — read its output.
- **Sync through `recyclarr-sync`**, cron's wrapper: it skips the run when an *arr is down and writes a one-line verdict to `~/.local/state/recyclarr/last`, which `boxstat` reads. It prints nothing itself. Read the log rather than the verdict's `changed-lines`: it also counts the "did not change" lines, so 2 is its floor — left that way by a decision recorded in the vault's Whatbox note.
- **A box-side edit is never pulled back**: `whatbox-pull` reports this row as `LINKED` and writes nothing. Carry the change here by hand.
- **The binary** is `~/bin/recyclarr`, pinned by a row in plumage `hosts/whatbox/promises.tsv`; upgrading it is plumage `docs/maintenance.md` § "Bump a Whatbox binary".

- **The battery tests what Radarr and Sonarr hold**, not the YAML. Each title goes through the service's parse endpoint, and the score is summed from that profile's live format scores, since the endpoint's own score follows whatever library entry the title matches. Every profile's minimum is 0, so `block` means a total below 0.

No other commands exist. There is no linting, build step or local validation: the preview on the box validates the YAML, and the battery validates the scoring.

## Publishing safety

This repo is public, so no file may name the box's ports or keys. `.githooks/pre-commit` refuses a commit when any staged file names a host with a port (loopback, an IP, or whatbox.ca), or a staged YAML file has a `base_url` or `api_key` that is not a `!secret` reference, or a URL outside a comment. It names line numbers only, never the value. It runs once the clone has `git config core.hooksPath .githooks`, and `--no-verify` skips it. `preen doctor` (plumage) runs the same hook on the working copy, and warns when that config is missing or plumage's row stops linking here. A new value goes into the box's `secrets.yml` — edited there, never in git — and the YAML references it with `!secret`.

## Hardware Constraints (These Drive All Scoring Decisions)

- **No transcoding**: Whatbox seedbox, Plex must Direct Play everything
- **No DTS**: Sonos Beam 2 cannot decode DTS; Plex can't transcode audio either. All DTS formats get `-10000`
- **No HDR10+**: LG C1 doesn't support it. HDR10+ Boost gets only `+100` (non-zero to act as tiebreaker, not a priority)
- **Dolby Vision needs HDR10 fallback**: Plex on the C1 plays DV profile 5, which has none, only from MP4; from MKV — nearly every release — it shifts magenta. DV without fallback gets `-10000` in every profile
- **No Remux/BR-DISK**: Too large for seedbox storage, and Direct Play makes raw disc pointless
- **No AV1**: Plex on the C1 always transcodes AV1, which the box cannot do. Blocked at `-10000` through the Unwanted group

## Profile Architecture

Two profiles per service, one per resolution tier:

| Service | Profile  | Upgrade until | Size envelope |
| ------- | -------- | ------------- | ------------- |
| Radarr  | HD-Kino  | Bluray-1080p  | ~6–16 GB      |
| Radarr  | UHD-Kino | Bluray-2160p  | ~20–35 GB     |
| Sonarr  | HD       | Bluray-1080p  | per-episode   |
| Sonarr  | UHD      | Bluray-2160p  | per-episode   |

**One guide group, otherwise no TRaSH baseline.** Neither service uses `score_set` or guide-profile `trash_id`s. The one import is the guide's `[Unwanted] Unwanted Formats` group (`custom_format_groups`), adopted whole at its `-10000` so a format the guide adds later arrives blocked rather than at 0. Its members are listed in the guide JSON (`docs/json/{radarr,sonarr}/cf-groups/unwanted-formats.json`), not here. An entry under `custom_formats` overrides a member per profile — LQ, LQ (Release Title), Bad Dual Groups and Extras carry their own scores — and a decline goes under the group's `exclude:` with its reason. Sonarr also `select`s two members the guide leaves off by default, BW and BR-DISK (BTN). Every other score is explicit in the YAML. (Recyclarr's `score_set` only picks which preset score applies to a CF listed _without_ an explicit `score:`; it never pulls formats in by itself.)

HQ release-group scoring therefore comes from explicitly listed tier CFs in both services — Radarr: `HD Bluray Tier 01–03`, `UHD Bluray Tier 01–03`, `WEB Tier 01–03`; Sonarr: `HD Bluray Tier 01–02`, `WEB Tier 01–03` (TRaSH publishes no Sonarr UHD Bluray tiers). HD Bluray tiers are also assigned to the UHD profiles, which fall back to Bluray-1080p when no 2160p release exists.

All profiles use `reset_unmatched_scores: true`, so any format score this config assigns neither explicitly nor through the group gets zeroed in the *arr instance.

## Scoring Conventions

- `-10000` = hard block (DTS, Remux, DV without fallback, and every Unwanted-group member without an explicit score — BR-DISK, 3D, Upscaled, AV1 and Generated Dynamic HDR among them)
- `-2500` to `-4500` = strong penalty (LQ, Bad Dual Groups, Obfuscated, Extras)
- `-10` to `-1000` = soft penalty (Retags, Scene, Theatrical Cut, x265 without HDR, LQ (Release Title), No-RlsGroup)
- `+5` to `+7` = tiebreakers (Repack/Proper, Repack2, Repack3 — grab the corrected release when otherwise equal)
- `+10` to `+100` = light preference (10bit, x265 in UHD, HDR10+, generic HDR +50)
- `+75` to `+200` = HQ release-group tiers (both services). Scaled down from TRaSH defaults (1600–1800) so audio/HDR scoring still dominates. Bluray tiers sit slightly above WEB tiers (200/150/100 vs 175/125/75), mirroring TRaSH's ordering.
- `+25` to `+800` = movie versions (Radarr): IMAX / IMAX Enhanced +800, Hybrid +500 UHD / +100 HD, Open Matte +350, Criterion / Special Edition +150, Remaster and 4K Remaster +25–125 depending on profile. Sonarr scores Hybrid identically. Theatrical Cut is the one negative version (`-50`).
- `+450` to `+1350` = strong preference (DD/DD+/ATMOS audio hierarchy)
- `+1000` = major feature boost (DV Boost)

Audio scoring hierarchy (same across all profiles):
DD+ ATMOS (1350) > DD+/ATMOS undefined (1250) > TrueHD ATMOS (750) > TrueHD (650) > DD (450)

Audio scores are intentionally flat across HD and UHD — the Beam 2 doesn't care what resolution precedes it, so the same hierarchy applies everywhere.

TrueHD is scored positively despite Beam 2 incompatibility because releases with TrueHD usually include a DD/AC3 fallback track.

HDR hierarchy (UHD profiles only): generic HDR (+50) stacks with DV Boost (+1000) and HDR10+ Boost (+100) to give DV+fallback ~+1050 > HDR10+ ~+150 > HDR10 +50 > SDR 0. DV without HDR10 fallback is blocked hard (-10000) regardless, and in the HD profiles too: the fallback requirement does not depend on resolution.

## Editing Guidelines

- Radarr and Sonarr use **different `trash_ids`** for the same format name. Never copy a trash_id between the radarr and sonarr sections.
- Every `trash_id` entry — CF or CF group — has an inline comment with its exact guide name (e.g., `# DTS-HD MA`). Keep comments verbatim-identical to the TRaSH guide `name` field so they can be verified mechanically against the guide JSON (`docs/json/{radarr,sonarr}/{cf,cf-groups}/*.json` in the TRaSH-Guides repo).
- A scoring change brings a row in `tests/releases.tsv` that would fail without it, shown failing before the sync and passing after.
- Scores assigned to profiles within the same `assign_scores_to` block typically share the same value across profiles unless there's a specific reason to differ (e.g., LQ is `-2500` for HD but `-4500` for UHD — UHD junk costs more disk and lives longer, so it's penalized harder).
