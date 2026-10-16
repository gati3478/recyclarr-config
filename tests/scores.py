"""Scores release titles with Radarr's and Sonarr's own matcher against their
live quality profiles, and checks each row of releases.tsv. Runs on the box,
sent there by tests/scores. Reads the API URLs and keys from recyclarr's
secrets.yml and prints neither.

The parse endpoint's own customFormatScore follows whatever library entry the
title happens to match, so the score here is computed per profile: the sum of
that profile's scores for the formats the matcher found. A profile rejects a
title scoring below its minimum, or in a quality it leaves off.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter

SECRETS = os.path.expanduser("~/.config/recyclarr/secrets.yml")
COLUMNS = 4
BLOCK_SCORE = "block:score"
BLOCK_QUALITY = "block:quality"
ALLOW = "allow"
KINDS = {BLOCK_SCORE, BLOCK_QUALITY, ALLOW}
LADDER = "ladder:"
UNPARSED = {None, "Unknown"}   # an unreadable title: no parsed info, or a quality of Unknown
# A title naming no resolution still parses, to a fallback picked by its source
# (WEB-DL reads as WEBDL-480p, BluRay as Bluray-720p, HDTV as SDTV) that looks
# like a real quality, so the title must name one. A bare 4K names none: both
# parsers fall back on it.
RESOLUTION = re.compile(r"(?i)(?:^|[._ ()\[\]-])(?:(?:480|576|720|1080|2160)[pi]|uhd)(?:$|[._ ()\[\]-])")


def read_secrets():
    found = {}
    with open(SECRETS) as f:
        for line in f:
            m = re.match(r"\s*(\w+)\s*:\s*(\S+)", line)
            if m:
                found[m.group(1)] = m.group(2).strip("\"'")
    return found


def allowed_qualities(profile):
    """A group's members follow the group's switch."""
    names = set()
    for item in profile["items"]:
        if item["allowed"]:
            names.update(m["quality"]["name"] for m in item.get("items") or [item])
    return names


class Arr:
    def __init__(self, url, key):
        self.url = url.rstrip("/")
        self.key = key
        self.profiles = {p["name"]: p for p in self.get("/api/v3/qualityprofile")}
        self.allowed = {name: allowed_qualities(p) for name, p in self.profiles.items()}
        self.parsed = {}

    def get(self, path):
        req = urllib.request.Request(self.url + path, headers={"X-Api-Key": self.key})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

    def parse(self, title):
        if title not in self.parsed:
            self.parsed[title] = self.get("/api/v3/parse?title=" + urllib.parse.quote(title))
        return self.parsed[title]

    def score(self, profile, title):
        matched = self.parse(title).get("customFormats", [])
        p = self.profiles[profile]
        by_id = {item["format"]: item["score"] for item in p["formatItems"]}
        total = sum(by_id.get(cf["id"], 0) for cf in matched)
        return total, [cf["name"] for cf in matched], p.get("minFormatScore", 0)

    def quality(self, profile, title):
        """The parsed quality's name, and whether the profile allows it."""
        parsed = self.parse(title)
        info = parsed.get("parsedMovieInfo") or parsed.get("parsedEpisodeInfo") or {}
        name = info.get("quality", {}).get("quality", {}).get("name")
        return name, name in self.allowed[profile]


def rows(tsv):
    """Each data row: its line number and its tab-separated fields."""
    for n, line in enumerate(tsv.splitlines(), 1):
        if line.strip() and not line.startswith("#"):
            yield n, line.split("\t")


def main(tsv):
    secrets = read_secrets()
    arrs = {}
    table = list(rows(tsv))
    rungs = Counter(tuple(f[:3]) for _, f in table if len(f) == COLUMNS and f[0].startswith(LADDER))
    ladders = {}   # (ladder, service, profile) -> the previous row's (line, score)
    passed = failed = 0
    for n, fields in table:
        if len(fields) != COLUMNS:
            print(f"FAIL  line {n}: {len(fields)} tab-separated fields, not {COLUMNS}")
            failed += 1
            continue
        kind, service, profile, title = fields
        if service + "_url" not in secrets:
            print(f"FAIL  line {n}: no service {service!r}")
            failed += 1
            continue
        if service not in arrs:
            arrs[service] = Arr(secrets[service + "_url"], secrets[service + "_api_key"])
        arr = arrs[service]
        if profile not in arr.profiles:
            print(f"FAIL  line {n}: {service} has no profile {profile!r}")
            failed += 1
            continue
        score, names, floor = arr.score(profile, title)
        quality, allowed = arr.quality(profile, title)
        grabbable = score >= floor and allowed
        faults = []
        if kind not in KINDS and not kind.startswith(LADDER):
            faults.append(f"unknown kind {kind!r}")
        if quality in UNPARSED:
            faults.append("no quality parsed")
        if not RESOLUTION.search(title):
            faults.append("the title names no resolution releases.tsv's header lists, so its quality may be the parser's fallback")
        if kind.startswith(LADDER) and rungs[(kind, service, profile)] < 2:
            faults.append("a one-row ladder compares nothing")
        why = ""
        if faults:
            ok = False
            why = f"  ({'; '.join(faults)})"
        elif kind == BLOCK_SCORE:
            ok = score < floor
        elif kind == BLOCK_QUALITY:
            ok = not allowed
        elif kind == ALLOW:
            ok = grabbable
        else:   # a ladder: faults above caught every other kind
            prev = ladders.get((kind, service, profile))
            ok = grabbable and (prev is None or score < prev[1])
            if not grabbable:
                why = "  (not grabbable)"
            elif prev is not None and not ok:
                why = f"  (must score below line {prev[0]}: {prev[1]})"
            ladders[(kind, service, profile)] = (n, score)
        off = "" if allowed else " (off)"
        print(f"{'PASS' if ok else 'FAIL'}  {service:<6} {profile:<8} {kind:<15} {score:>6}  {title}  {quality}{off}  [{', '.join(names)}]{why}")
        passed += ok
        failed += not ok
    if passed + failed == 0:
        print("== no rows: nothing was checked ==")
        sys.exit(1)
    print(f"== {passed} passed, {failed} failed ==")
    sys.exit(1 if failed else 0)
