#!/usr/bin/env python3
"""Fetch citation statistics from ADS and Google Scholar cache.

Usage:
    python fetch_stats.py                   # print stats
    python fetch_stats.py --update-pages    # also patch stats line in about.md and cv.md

Dependencies:
    pip install requests

"""

import json
import os
import re
import requests
from datetime import date

# ── Configuration ─────────────────────────────────────────────────────────────
ADS_TOKEN     = "7rbhCKGe8EGuSLM3XpV2RZ1v5RpjvnOqUgb13X7i"
LIBRARY_ID    = "nThU2Yw3SUytqSYjksZ8uA"
SCHOLAR_ID    = "4O8TNrgAAAAJ"
SCHOLAR_CACHE = os.path.join(os.path.expanduser("~/Code/CV_stuff"), "scholar_cache.json")

PAGES_TO_UPDATE = [
    "_posts/2019-04-07-cv.md",
    "_posts/2019-04-06-Publications.md",
]
# ──────────────────────────────────────────────────────────────────────────────

HEADERS = {"Authorization": f"Bearer {ADS_TOKEN}"}


def fetch_ads_bibcodes():
    url    = f"https://api.adsabs.harvard.edu/v1/biblib/libraries/{LIBRARY_ID}"
    resp   = requests.get(url, headers=HEADERS, params={"start": 0, "rows": 500})
    resp.raise_for_status()
    return [d["bibcode"] for d in resp.json()["solr"]["response"]["docs"]]


def fetch_ads_metrics(bibcodes):
    url  = "https://api.adsabs.harvard.edu/v1/metrics"
    body = {"bibcodes": bibcodes, "types": ["basic", "citations", "indicators"]}
    resp = requests.post(url, headers={**HEADERS, "Content-Type": "application/json"},
                         json=body)
    resp.raise_for_status()
    data = resp.json()

    basic      = data.get("basic stats", {})
    basic_ref  = data.get("basic stats refereed", {})
    cite       = data.get("citation stats", {})
    indicators = data.get("indicators", {})

    return {
        "total_papers":       basic.get("number of papers", 0),
        "refereed_papers":    basic_ref.get("number of papers", 0),
        "total_citations":    cite.get("total number of citations", 0),
        "refereed_citations": cite.get("total number of refereed citations", 0),
        "h_index":            indicators.get("h", 0),
    }


def get_scholar_stats(cache_path):
    try:
        from scholarly import scholarly as _scholarly
        print("  Fetching from Google Scholar live…")
        author = _scholarly.search_author_id(SCHOLAR_ID)
        author = _scholarly.fill(author, sections=["basics", "indices"])
        stats = {
            "citedby":  author.get("citedby", 0),
            "hindex":   author.get("hindex", 0),
            "i10index": author.get("i10index", 0),
        }
        try:
            with open(cache_path) as f:
                cached = json.load(f)
        except (OSError, json.JSONDecodeError):
            cached = {}
        cached.update({**stats, "fetched_at": date.today().isoformat()})
        with open(cache_path, "w") as f:
            json.dump(cached, f, indent=2, ensure_ascii=False)
        print(f"  Cache updated.")
        return stats
    except Exception as e:
        print(f"  [ FALLBACK ] Scholar live fetch failed ({e}); reading cache")
    try:
        with open(cache_path) as f:
            data = json.load(f)
        return {
            "citedby":  data.get("citedby", 0),
            "hindex":   data.get("hindex", 0),
            "i10index": data.get("i10index", 0),
        }
    except (OSError, json.JSONDecodeError) as e:
        print(f"  [ WARNING ] Cache also unavailable ({e}); using ADS stats only")
        return None


def build_stats_line(ads, scholar, month_year):
    papers = ads["refereed_papers"] or ads["total_papers"]
    sep    = " &nbsp;&#9632;&nbsp; "
    if scholar:
        parts = [
            f"{papers} peer-reviewed publications and preprints",
            f"{scholar['citedby']:,} citations (Scholar)",
            f"h-index {scholar['hindex']} (Scholar)",
            f"i10-index {scholar['i10index']} (Scholar)",
            month_year,
        ]
    else:
        parts = [
            f"{papers} peer-reviewed publications and preprints",
            f"~{ads['total_citations']:,} citations (ADS)",
            f"h-index {ads['h_index']} (ADS)",
            month_year,
        ]
    return f"*{sep.join(parts)}*"


def patch_stats_in_file(path, new_line):
    pattern = re.compile(
        r"\*+\d[\d,]*\s+peer-reviewed publications.*?20\d\d\*",
        re.DOTALL,
    )
    with open(path) as f:
        content = f.read()
    updated, n = pattern.subn(new_line, content)
    if n:
        with open(path, "w") as f:
            f.write(updated)
        print(f"  Updated stats line in {path}")
    else:
        print(f"  No stats line found to replace in {path}")


def main():
    import sys
    update_pages = "--update-pages" in sys.argv

    print("Fetching ADS library bibcodes…")
    bibcodes = fetch_ads_bibcodes()
    print(f"  {len(bibcodes)} bibcodes found")

    print("Fetching ADS metrics…")
    ads = fetch_ads_metrics(bibcodes)

    print("Fetching Google Scholar stats…")
    scholar = get_scholar_stats(SCHOLAR_CACHE)

    month_year = date.today().strftime("%B %Y")

    print("\n── ADS ──────────────────────────────────────")
    print(f"  Papers (total):     {ads['total_papers']}")
    print(f"  Papers (refereed):  {ads['refereed_papers']}")
    print(f"  Citations (total):  {ads['total_citations']}")
    print(f"  Citations (ref'd):  {ads['refereed_citations']}")
    print(f"  h-index:            {ads['h_index']}")

    if scholar:
        print("\n── Scholar ──────────────────────────────────")
        print(f"  Citations:          {scholar['citedby']}")
        print(f"  h-index:            {scholar['hindex']}")
        print(f"  i10-index:          {scholar['i10index']}")

    stats_line = build_stats_line(ads, scholar, month_year)
    print(f"\nStats line:\n  {stats_line}")

    if update_pages:
        print("\nPatching pages…")
        for path in PAGES_TO_UPDATE:
            if os.path.exists(path):
                patch_stats_in_file(path, stats_line)
            else:
                print(f"  Not found: {path}")


if __name__ == "__main__":
    main()
