# Recyclarr Configuration for Whatbox + LG C1 + Sonos Beam 2

Opinionated Recyclarr config for a Direct Play-only Plex setup with specific hardware constraints.

## Hardware Context

- **Server**: Whatbox seedbox (no transcoding, Direct Play only)
- **Display**: LG C1 OLED (HDR10, Dolby Vision; no HDR10+)
- **Audio**: Sonos Beam 2 soundbar (Dolby Digital, DD+, Atmos; no DTS)
- **Client**: Plex on webOS

## Configuration Philosophy

One profile per resolution on each side — two Radarr profiles for movies, two Sonarr profiles for TV. Every score is explicit in the YAML: no TRaSH score-set baselines, no hidden guide defaults. What you read in the config is the complete scoring model, and `reset_unmatched_scores` zeroes anything it doesn't mention.

### Radarr Profiles

- **HD-Kino** (~6–16 GB): 1080p cap, premium WEB/BD groups, rich audio
- **UHD-Kino** (~20–35 GB): up to 2160p, HDR/DV, UHD BD/WEB top tiers, IMAX ok

### Sonarr Profiles

- **HD**: 1080p cap for TV series
- **UHD**: up to 2160p HDR/DV for prestige TV

## Key Design Decisions

**Audio**

- DTS blocked completely (hard `-10000`) — Beam 2 can't decode it, and Plex can't be allowed to transcode audio
- TrueHD scored positively despite incompatibility — releases always include AC3/DD fallback tracks
- DD+ Atmos prioritized heavily — native Beam 2 support, excellent quality

**Video**

- HDR10+ mostly ignored (C1 doesn't support it; scored only as a tiebreaker)
- Dolby Vision preferred with HDR10 fallback required; DV-only blocked hard
- x265 penalized on 1080p releases without HDR (encoder-noise territory), lightly favored on UHD where it pairs with HDR

**Release Groups**

- TRaSH HQ tier formats (HD/UHD Bluray tiers, WEB tiers) applied in both services, scaled from TRaSH's 1600–1800 defaults down to +75…+200 — group quality breaks ties but never outvotes audio/HDR scoring

**Movie Versions (Radarr)**

- IMAX / IMAX Enhanced strongly preferred (+800); Hybrid, Open Matte, Criterion, Special Edition, and remasters get graded boosts; Theatrical Cut slightly penalized when a better version exists

**Universal Blocks & Nudges**

- Remux/BR-DISK blocked (too large; pointless for Direct Play)
- Scene releases slightly penalized (prefer P2P quality)
- Low-quality, obfuscated, and re-tagged releases heavily penalized
- Repack/Proper scored +5…+7 as pure tiebreakers — grab the corrected release when otherwise equal

## Usage

1. Install [Recyclarr](https://recyclarr.dev/) (or use the Docker image)
2. Copy `recyclarr-template.yml` to `recyclarr.yml`
3. Replace the four placeholders: `RADARR_PORT`, `RADARR_API_KEY`, `SONARR_PORT`, `SONARR_API_KEY`
4. Preview, then apply:

```sh
recyclarr sync --preview
recyclarr sync
```

## Why These Choices?

The scoring is opinionated toward a Direct Play workflow where file size matters but quality can't be sacrificed. One profile per resolution pursues the best release that still fits the size envelope (~6–16 GB at 1080p, ~20–35 GB at 2160p) — no 60 GB remuxes, no garbage compressions. Everything respects the hard constraint: if Plex can't Direct Play it, it won't play at all.
