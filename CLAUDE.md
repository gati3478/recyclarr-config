# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Recyclarr configuration for a Direct Play-only Plex setup on a Whatbox seedbox. No source code, no build system — one YAML file that `recyclarr sync` pushes to Radarr and Sonarr.

## Files

- `recyclarr.yml` — the live config, versioned here. It names no port and no key: `base_url` and `api_key` are `!secret radarr_url` / `!secret radarr_api_key` and the Sonarr pair, resolved on the box from `~/.config/recyclarr/secrets.yml`, which exists only there. plumage deploys it through a link — `~/Development/plumage/hosts/whatbox/files/recyclarr/recyclarr.yml` → `../../../../../recyclarr/recyclarr.yml` — so a plumage clone needs this repo cloned beside it.
- `README.md` — the public design write-up.
- `.githooks/pre-commit` — the publishing guard (below).
- `tests/` — the scoring battery: `releases.tsv` holds release titles and what each profile must do with them; `scores` checks them on the box. `parity` checks, locally, that Radarr and Sonarr score the formats they share alike.

The file carries a `yaml-language-server` schema header, so schema-aware editors validate it on save.

## Syncing and deploying

Recyclarr is not installed on this machine, and `sync` reaches Radarr and Sonarr only from the box, so every deploy goes through plumage and every check but `tests/parity` runs on the box:

```
tests/parity                                            # locally, before the deploy: shared formats scored alike
~/Development/plumage/hosts/whatbox/bin/whatbox-apply   # deploys the edited file, re-checks
ssh -tt whatbox '~/bin/recyclarr sync --preview'        # the parse and the diff, against today's guide
ssh whatbox '~/bin/recyclarr-sync; tail -n 20 ~/.local/state/recyclarr/sync.log'   # the sync and its log, or wait for cron: Monday 04:00 UTC
tests/scores                                            # after the sync: release titles scored by the *arrs' own matcher
```

- **Never `scp` straight onto the box**: `preen doctor` reports the drift, and `whatbox-apply` puts the governed copy back.
- **The preview needs a PTY.** Its diff renders only to a terminal; `-tt` forces one even when stdin is not a terminal, as in a Claude Code session (one `-t` does not). Without it the preview prints log lines and no diff, which reads as clean. It also exits 0 on a parse error — read its output. Its Media Management section is not a diff: it prints the configured value on every run, never "No changes".
- **Sync through `recyclarr-sync`**, cron's wrapper: it skips the run when an *arr is down and writes a one-line verdict to `~/.local/state/recyclarr/last`, which `boxstat` reads. It prints nothing itself. Read the log rather than the verdict's `changed-lines`: it also counts the "did not change" lines, so 2 is its floor — left that way by a decision recorded in the vault's Whatbox note.
- **A box-side edit is never pulled back**: `whatbox-pull` reports this row as `LINKED` and writes nothing. Carry the change here by hand.
- **The binary** is `~/bin/recyclarr`, pinned by a row in plumage `hosts/whatbox/promises.tsv`; upgrading it is plumage `docs/maintenance.md` § "Bump a Whatbox binary".

- **The battery tests what Radarr and Sonarr hold**, not the YAML. Each title goes through the service's parse endpoint, and the score is summed from that profile's live format scores, since the endpoint's own score follows whatever library entry the title matches. Each row names one kind: `block:score`, a total below the profile's minimum (0 in every profile); `block:quality`, a quality the profile leaves off; `allow`, neither; `ladder:NAME`, allowed and strictly below the previous row with the same name, service and profile. A title whose quality parses to nothing or to Unknown fails whatever its kind. `tests/scores TABLE` checks another table, which is how a negative control runs.

Nothing else runs: no linting, no build step. Locally, `tests/parity` checks the scores and the pre-commit hook checks for leaks; the preview on the box validates the YAML against today's guide, and the battery validates the scoring.

## Publishing safety

This repo is public, so no file may name the box's ports or keys. `.githooks/pre-commit` refuses a commit when any staged file names a host with a port (loopback, an IP, or whatbox.ca), or a staged YAML file has a `base_url` or `api_key` that is not a `!secret` reference, or a URL outside a comment. It names line numbers only, never the value. It runs once the clone has `git config core.hooksPath .githooks`, and `--no-verify` skips it. `preen doctor` (plumage) runs the same hook on the working copy, and warns when that config is missing or plumage's row stops linking here. A new value goes into the box's `secrets.yml` — edited there, never in git — and the YAML references it with `!secret`.

## Hardware Constraints (These Drive All Scoring Decisions)

- **No transcoding**: Whatbox seedbox, Plex must Direct Play everything
- **No DTS**: Sonos Beam 2 cannot decode DTS; Plex can't transcode audio either. All DTS formats get `-10000`
- **No HDR10+**: LG C1 doesn't support it. HDR10+ Boost gets only `+100` (non-zero to act as tiebreaker, not a priority)
- **Dolby Vision needs HDR10 fallback**: Plex on the C1 plays DV profile 5, which has none, only from MP4; from MKV — nearly every release — it shifts magenta. DV without fallback gets `-10000` in every profile
- **No Remux/BR-DISK**: Too large for seedbox storage, and Direct Play makes raw disc pointless. No profile allows a Remux quality, and the Unwanted group blocks BR-DISK
- **No AV1**: Plex on the C1 always transcodes AV1, which the box cannot do. Blocked at `-10000` through the Unwanted group

## Profile Architecture

Two profiles per service, one per resolution tier:

| Service | Profile  | Upgrade until |
| ------- | -------- | ------------- |
| Radarr  | HD-Kino  | Bluray-1080p  |
| Radarr  | UHD-Kino | Bluray-2160p  |
| Sonarr  | HD       | Bluray-1080p  |
| Sonarr  | UHD      | Bluray-2160p  |

**One guide group, otherwise no TRaSH baseline.** Neither service uses `score_set` or guide-profile `trash_id`s. The one import is the guide's `[Unwanted] Unwanted Formats` group (`custom_format_groups`), adopted whole at its `-10000` so a format the guide adds later arrives blocked rather than at 0. Its members are listed in the guide JSON (`docs/json/{radarr,sonarr}/cf-groups/unwanted-formats.json`), not here. An entry under `custom_formats` overrides a member per profile — LQ, LQ (Release Title), Bad Dual Groups and Extras carry their own scores — and a decline goes under the group's `exclude:` with its reason. Sonarr also `select`s BW, a member the guide leaves off by default. BR-DISK (BTN) stays off: it reads H.264 and H.265 as a disc codec, so it would block Blu-ray encodes named that way; the standard BR-DISK already blocks disc titles, and no indexer here is BTN. Every other score is explicit in the YAML. (Recyclarr's `score_set` only picks which preset score applies to a CF listed _without_ an explicit `score:`; it never pulls formats in by itself.)

HQ release-group scoring therefore comes from explicitly listed tier CFs in both services — Radarr: `HD Bluray Tier 01–03`, `UHD Bluray Tier 01–03`, `WEB Tier 01–03`; Sonarr: `HD Bluray Tier 01–02`, `WEB Tier 01–03` (TRaSH publishes no Sonarr UHD Bluray tiers). HD Bluray tiers are also assigned to the UHD profiles, which fall back to Bluray-1080p when no 2160p release exists.

All profiles use `reset_unmatched_scores: true`, so any format score this config assigns neither explicitly nor through the group gets zeroed in the *arr instance.

Both instances set `media_management: propers_and_repacks: do_not_prefer`, as recyclarr's schema advises when custom formats handle repacks: the Repack/Proper formats rank a corrected release, not the *arrs' own preference for one.

## Scoring Conventions

Bands, not lists: the YAML says which format sits where.

- `-10000` = hard block: what the hardware cannot play, and every member of the guide's Unwanted group this config does not score itself
- `-2500` to `-4500` = strong penalty: releases rarely worth having
- `-10` to `-1000` = soft penalty: a worse or more doubtful variant, which good audio can still outweigh
- `+5` to `+7` = tiebreakers: grab the corrected release when otherwise equal
- `+10` to `+100` = light preference
- `+75` to `+200` = HQ release-group tiers, scaled down from TRaSH's 1600–1800 so audio and HDR scoring still dominate; Bluray tiers sit slightly above WEB tiers, as in TRaSH's ordering
- `+50` to `+800` = versions, graded
- `+450` to `+1350` = strong preference: the audio hierarchy below
- `+1000` = major feature boost: Dolby Vision

Audio scoring hierarchy (same across all profiles):
DD+ ATMOS (1350) > DD+/ATMOS undefined (1250) > TrueHD ATMOS (750) > TrueHD (650) > DD (450)

Audio scores are intentionally flat across HD and UHD — the Beam 2 doesn't care what resolution precedes it, so the same hierarchy applies everywhere.

TrueHD is scored positively despite Beam 2 incompatibility because releases with TrueHD usually include a DD/AC3 fallback track.

HDR hierarchy (UHD profiles only): generic HDR (+50) stacks with DV Boost (+1000) and HDR10+ Boost (+100) to give DV+fallback ~+1050 > HDR10+ ~+150 > HDR10 +50 > SDR 0. DV without HDR10 fallback is blocked hard (-10000) regardless, and in the HD profiles too: the fallback requirement does not depend on resolution.

## Editing Guidelines

- Radarr and Sonarr use **different `trash_ids`** for the same format name. Never copy a trash_id between the radarr and sonarr sections.
- Every `trash_id` entry — CF or CF group — has an inline comment with its exact guide name (e.g., `# DTS-HD MA`). Keep comments verbatim-identical to the TRaSH guide `name` field so they can be verified mechanically against the guide JSON (`docs/json/{radarr,sonarr}/{cf,cf-groups}/*.json` in the TRaSH-Guides repo).
- A scoring change brings a row in `tests/releases.tsv` that would fail without it, shown failing before the sync and passing after.
- A score change in one service either mirrors to the other or joins `tests/parity`'s allowlist with its reason.
- Scores assigned to profiles within the same `assign_scores_to` block typically share the same value across profiles unless there's a specific reason to differ (e.g., LQ is `-2500` for HD but `-4500` for UHD — UHD junk costs more disk and lives longer, so it's penalized harder).
