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

SECRETS = os.path.expanduser("~/.config/recyclarr/secrets.yml")
BLOCK_SCORE = "block:score"
BLOCK_QUALITY = "block:quality"
ALLOW = "allow"
LADDER = "ladder:"
UNPARSED = {None, "Unknown"}   # an unreadable title: Sonarr parses no info, Radarr says Unknown


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


def main(tsv):
    secrets = read_secrets()
    arrs = {}
    ladders = {}   # (ladder, service, profile) -> the previous row's (line, score)
    passed = failed = 0
    for n, line in enumerate(tsv.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        kind, service, profile, title = line.split("\t")
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
        why = ""
        if quality in UNPARSED:
            ok = False
            why = "  (no quality parsed)"
        elif kind == BLOCK_SCORE:
            ok = score < floor
        elif kind == BLOCK_QUALITY:
            ok = not allowed
        elif kind == ALLOW:
            ok = grabbable
        elif kind.startswith(LADDER):
            prev = ladders.get((kind, service, profile))
            ok = grabbable and (prev is None or score < prev[1])
            if not grabbable:
                why = "  (not grabbable)"
            elif prev is not None and not ok:
                why = f"  (must score below line {prev[0]}: {prev[1]})"
            ladders[(kind, service, profile)] = (n, score)
        else:
            ok = False
            why = f"  (unknown kind {kind!r})"
        off = "" if allowed else " (off)"
        print(f"{'PASS' if ok else 'FAIL'}  {service:<6} {profile:<8} {kind:<15} {score:>6}  {title}  {quality}{off}  [{', '.join(names)}]{why}")
        passed += ok
        failed += not ok
    print(f"== {passed} passed, {failed} failed ==")
    sys.exit(1 if failed else 0)
