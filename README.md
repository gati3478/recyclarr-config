# Recyclarr Configuration for Whatbox + LG C1 + Sonos Beam 2

Optimized Recyclarr config for a Direct Play-only Plex setup with specific hardware constraints.

## Hardware Context

- **Server**: Whatbox seedbox (no transcoding, Direct Play only)
- **Display**: LG C1 OLED (HDR10, Dolby Vision support; no HDR10+)
- **Audio**: Sonos Beam 2 soundbar (Dolby Digital, DD+, Atmos; no DTS support)
- **Client**: Plex on webOS

## Configuration Philosophy

Four Radarr profiles targeting different use cases, two Sonarr profiles for TV content. All profiles respect hardware limitations while maximizing quality within constraints.

### Radarr Profiles

- **HD-Lite** (~2GB): Efficient 1080p encodes, x265 preferred, for casual viewing
- **HD-Premium** (~6GB): High-quality 1080p from top-tier release groups
- **UHD-Lite** (~9GB): Efficient 4K with HDR/DV support, compressed but clean
- **UHD-Premium** (~25GB): Premium 4K encodes from top release groups

### Sonarr Profiles

- **HD**: Balanced 1080p for TV series
- **UHD**: 4K HDR/DV for prestige TV

## Key Design Decisions

**Audio Handling**
- DTS formats blocked completely (hard -10000) - Beam 2 can't decode, Plex can't be allowed to transcode audio
- TrueHD scored positively despite incompatibility - releases always include AC3/DD fallback tracks anyway
- DD+ Atmos prioritized heavily - native Beam 2 support, excellent quality

**Video Optimization**
- HDR10+ mostly ignored (C1 doesn't support it natively)
- Dolby Vision preferred with HDR10 fallback required
- x265 heavily favored in "Lite" profiles for size efficiency
- Release group scoring inverted for Lite profiles - mid-tier groups often compress better than top-tier

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

The scoring is opinionated toward a Direct Play workflow where file size matters but quality can't be sacrificed. "Lite" profiles chase compression without accepting garbage encodes. "Premium" profiles pursue top-tier releases but stay within reasonable size bounds (no 60GB remuxes). Everything respects the hard constraint: if Plex can't Direct Play it, it won't play at all.
