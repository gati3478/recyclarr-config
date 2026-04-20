# Recyclarr Configuration for Whatbox + LG C1 + Sonos Beam 2

Optimized Recyclarr config for a Direct Play-only Plex setup with specific hardware constraints.

## Hardware Context

- **Server**: Whatbox seedbox (no transcoding, Direct Play only)
- **Display**: LG C1 OLED (HDR10, Dolby Vision support; no HDR10+)
- **Audio**: Sonos Beam 2 soundbar (Dolby Digital, DD+, Atmos; no DTS support)
- **Client**: Plex on webOS

## Configuration Philosophy

One profile per resolution on each side — two Radarr profiles for movies, two Sonarr profiles for TV. All profiles respect hardware limitations while maximizing quality within constraints.

### Radarr Profiles

- **HD-Kino** (`sqp-1-1080p` base, ~6–16 GB): 1080p cap, premium WEB/BD groups and lossless audio
- **UHD-Kino** (`sqp-1-2160p` base, ~20–35 GB): up to 2160p, UHD BD/WEB top tiers, IMAX ok

### Sonarr Profiles

- **HD**: 1080p cap for TV series
- **UHD**: up to 2160p HDR/DV for prestige TV

## Key Design Decisions

**Audio Handling**

- DTS formats blocked completely (hard -10000) - Beam 2 can't decode, Plex can't be allowed to transcode audio
- TrueHD scored positively despite incompatibility - releases always include AC3/DD fallback tracks anyway
- DD+ Atmos prioritized heavily - native Beam 2 support, excellent quality

**Video Optimization**

- HDR10+ mostly ignored (C1 doesn't support it natively; scored only as a tiebreaker)
- Dolby Vision preferred with HDR10 fallback required; DV-only blocked hard
- x265 penalized on 1080p releases without HDR (encoder-noise territory), lightly favored on UHD where it pairs with HDR

**Universal Blocks**

- Remux/BR-DISK blocked (too large, Direct Play requirement makes them pointless)
- Scene releases slightly penalized (prefer P2P quality)
- Low-quality, obfuscated, and re-tagged releases heavily penalized

## Usage

1. Install [Recyclarr](https://recyclarr.dev/)
2. Update `base_url` and `api_key` for your instances
3. Rename the file to `recyclarr.yml`
4. Run: `recyclarr sync`

## Why These Choices?

The scoring is opinionated toward a Direct Play workflow where file size matters but quality can't be sacrificed. One profile per resolution pursues the best release that still fits the size envelope (~6–16 GB at 1080p, ~20–35 GB at 2160p) — no 60 GB remuxes, no garbage compressions. Everything respects the hard constraint: if Plex can't Direct Play it, it won't play at all.
