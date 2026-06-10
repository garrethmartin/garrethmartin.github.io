#!/usr/bin/env python3
"""Generate the publications page for garrethmartin.github.io.

Fetches papers from an ADS library and writes _posts/2019-04-06-Publications.md.
Run from the repo root:  python generate_publist.py
"""

import json
import os
import re
import requests
from collections import defaultdict

ADS_TOKEN    = "7rbhCKGe8EGuSLM3XpV2RZ1v5RpjvnOqUgb13X7i"
LIBRARY_ID   = "nThU2Yw3SUytqSYjksZ8uA"
OUT_FILE     = "_posts/2019-04-06-Publications.md"
HEADERS      = {"Authorization": f"Bearer {ADS_TOKEN}"}
SCHOLAR_CACHE = os.path.join("/home/ppzgm/Code/CV_stuff", "scholar_cache.json")


def latex_to_utf8(text):
    replacements = {
        r"\'a": "á", r'\"a': "ä", r"\'e": "é", r'\"e': "ë",
        r"\'i": "í", r'\"i': "ï", r"\'o": "ó", r'\"o': "ö",
        r"\'u": "ú", r'\"u': "ü", r"\~n": "ñ", r"\c{c}": "ç",
        r"\'A": "Á", r'\"A': "Ä", r"\&": "&", r"``": "“", r"''": "”",
    }
    for latex, char in replacements.items():
        text = text.replace(latex, char)
    return text


def _norm_title(text):
    t = text.lower()
    t = t.replace("–", "-").replace("—", "-")
    t = re.sub(r"\s+", " ", t).strip(" .")
    t = t.replace("-", "")
    return t


def load_scholar_data(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"WARNING: could not load scholar cache ({e}); skipping Scholar stats")
        return {}, {}
    citations = {
        _norm_title(p["title"]): p["num_citations"]
        for p in data.get("publications", [])
        if p.get("num_citations", 0) > 0
    }
    return data, citations


def format_paper(p, scholar_citations):
    raw_title = (p.get("title") or [""])[0]
    title     = f"*{latex_to_utf8(raw_title)}*"
    authors   = [latex_to_utf8(a) for a in (p.get("author") or [])]
    authors   = [f"**{a}**" if "Martin, G" in a else a for a in authors]
    author_str = ", ".join(authors)
    year    = p.get("year") or "n.d."
    date    = p.get("pubdate") or ""
    month   = date.split("-")[1] if date else ""
    bibstem = p.get("bibstem") or []
    journal = bibstem[0] if bibstem else (p.get("pub") or "")
    volume  = p.get("volume") or ""
    pages   = p.get("page") or []
    page    = pages[0] if pages else ""
    dois    = p.get("doi") or []
    doi     = dois[0] if dois else ""
    ref     = f"{journal} {volume}, {page}".strip()
    ref_str = f"[{ref}](https://doi.org/{doi})" if doi else ref

    cit_str = ""
    if scholar_citations:
        key = _norm_title(latex_to_utf8(raw_title))
        n   = scholar_citations.get(key, 0)
        if n:
            cit_str = f" | {n:,} citations"

    return f"{title}  \n{author_str}  \n{month}/{year} | {ref_str}{cit_str}"


def main():
    scholar_data, scholar_citations = load_scholar_data(SCHOLAR_CACHE)

    lib_url  = f"https://api.adsabs.harvard.edu/v1/biblib/libraries/{LIBRARY_ID}"
    lib_resp = requests.get(lib_url, headers=HEADERS, params={"start": 0, "rows": 500})
    lib_resp.raise_for_status()
    solr     = lib_resp.json()["solr"]["response"]
    bibcodes = [d["bibcode"] for d in solr["docs"]]
    print(f"Library contains {solr['numFound']} docs, fetching {len(bibcodes)}.")

    query        = " OR ".join(f"bibcode:{bc}" for bc in bibcodes)
    search_resp  = requests.get(
        "https://api.adsabs.harvard.edu/v1/search/query",
        headers=HEADERS,
        params={
            "q":    query,
            "fl":   "title,author,pubdate,year,pub,bibstem,volume,page,doi",
            "rows": len(bibcodes),
        },
    )
    search_resp.raise_for_status()
    papers = search_resp.json()["response"]["docs"]

    first_author_papers = []
    all_by_year = defaultdict(list)

    for p in papers:
        year  = p.get("year") or "0"
        date  = p.get("pubdate") or ""
        month = int(date.split("-")[1]) if date and "-" in date else 0
        formatted = format_paper(p, scholar_citations)
        authors   = [latex_to_utf8(a) for a in (p.get("author") or [])]
        if authors and authors[0].startswith("Martin, G"):
            first_author_papers.append((year, month, formatted))
        all_by_year[year].append((month, formatted))

    first_author_papers.sort(key=lambda x: (x[0], x[1]), reverse=True)
    for year in all_by_year:
        all_by_year[year].sort(key=lambda x: x[0], reverse=True)

    sep = " &nbsp;&#9632;&nbsp; "
    if scholar_data:
        stats_parts = [
            f"{len(papers)} peer-reviewed publications and preprints",
            f"{scholar_data['citedby']:,} citations (Scholar)",
            f"h-index {scholar_data['hindex']} (Scholar)",
            f"i10-index {scholar_data['i10index']} (Scholar)",
            __import__('datetime').date.today().strftime('%B %Y'),
        ]
    else:
        stats_parts = [
            f"{len(papers)} peer-reviewed publications and preprints",
            "citations (ADS)",
            "h-index (ADS)",
            __import__('datetime').date.today().strftime('%B %Y'),
        ]
    stats_line = f"*{sep.join(stats_parts)}*"

    lines = [
        "---",
        "layout: post",
        "title: Publications",
        "cover: NHz.png",
        "date:   2013-12-09 12:00:00",
        "categories: posts",
        "---",
        "",
        "[`ADS Library`](https://ui.adsabs.harvard.edu/public-libraries/nThU2Yw3SUytqSYjksZ8uA \"ADS library\")"
        f"{sep}[`Google Scholar`](https://scholar.google.com/citations?user=4O8TNrgAAAAJ \"Google Scholar\")"
        f"{sep}[`CV (PDF)`](/files/CV_Martin.pdf \"Curriculum vitae\")"
        f"{sep}[`Publication list (PDF)`](/files/publication_list.pdf \"Publication list\")",
        "",
        stats_line,
        "",
        "## First-author publications",
        "",
    ]

    for _, _, entry in first_author_papers:
        lines.append(entry + "\n")

    lines += ["", "## All peer-reviewed publications and preprints", ""]

    for year in sorted(all_by_year.keys(), reverse=True):
        lines.append(f"### {year}\n")
        for _, entry in all_by_year[year]:
            indented = "\n".join(">" + line for line in entry.split("\n"))
            lines.append(indented + "\n")

    with open(OUT_FILE, "w") as f:
        f.write("\n".join(lines))

    print(f"Written to {OUT_FILE}")


if __name__ == "__main__":
    main()
