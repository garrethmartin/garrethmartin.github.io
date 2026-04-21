#!/usr/bin/env python3
"""Generate the publications page for garrethmartin.github.io.

Fetches papers from an ADS library and writes _posts/2019-04-06-Publications.md.
Run from the repo root:  python generate_publist.py
"""

import ads
import requests
from collections import defaultdict

ADS_TOKEN  = "7rbhCKGe8EGuSLM3XpV2RZ1v5RpjvnOqUgb13X7i"
LIBRARY_ID = "nThU2Yw3SUytqSYjksZ8uA"
OUT_FILE   = "_posts/2019-04-06-Publications.md"
HEADERS    = {"Authorization": f"Bearer {ADS_TOKEN}"}


def latex_to_utf8(text):
    # str.replace rather than re.sub — all replacements are literal strings
    replacements = {
        r"\'a": "á", r'\"a': "ä", r"\'e": "é", r'\"e': "ë",
        r"\'i": "í", r'\"i': "ï", r"\'o": "ó", r'\"o': "ö",
        r"\'u": "ú", r'\"u': "ü", r"\~n": "ñ", r"\c{c}": "ç",
        r"\'A": "Á", r'\"A': "Ä", r"\&": "&", r"``": "\u201c", r"''": "\u201d",
    }
    for latex, char in replacements.items():
        text = text.replace(latex, char)
    return text


def format_paper(p):
    title = f"*{latex_to_utf8(p.title[0])}*"
    authors = [latex_to_utf8(a) for a in p.author]
    authors = [f"**{a}**" if "Martin, G" in a else a for a in authors]
    author_str = ", ".join(authors)
    year   = p.year or "n.d."
    date   = p.pubdate
    month  = date.split("-")[1] if date else ""
    journal = p.bibstem[0] if p.bibstem else (p.pub or "")
    volume = p.volume or ""
    page   = p.page[0] if p.page else ""
    doi    = p.doi[0] if p.doi else ""
    doi_str = f"https://doi.org/{doi}" if doi else ""
    return f"{title}  \n{author_str}  \n{month}/{year} | {journal} {volume}, {page} | {doi_str}"


def main():
    params = {"start": 0, "rows": 500}
    url    = f"https://api.adsabs.harvard.edu/v1/biblib/libraries/{LIBRARY_ID}"
    resp   = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    solr      = resp.json()["solr"]["response"]
    bibcodes  = [d["bibcode"] for d in solr["docs"]]
    print(f"Library contains {solr['numFound']} docs, fetching {len(bibcodes)}.")

    ads.config.token = ADS_TOKEN
    query  = " OR ".join(f"bibcode:{bc}" for bc in bibcodes)
    papers = list(ads.SearchQuery(
        q=query,
        fl=["title", "author", "pubdate", "year", "pub", "bibstem", "volume", "page", "doi"],
        rows=len(bibcodes),
    ))

    first_author_papers = []
    all_by_year = defaultdict(list)

    for p in papers:
        year  = p.year or "0"
        date  = p.pubdate
        month = int(date.split("-")[1]) if date and "-" in date else 0
        formatted = format_paper(p)
        authors   = [latex_to_utf8(a) for a in p.author]
        if authors and authors[0].startswith("Martin, G"):
            first_author_papers.append((year, month, formatted))
        all_by_year[year].append((month, formatted))

    first_author_papers.sort(key=lambda x: (x[0], x[1]), reverse=True)
    for year in all_by_year:
        all_by_year[year].sort(key=lambda x: x[0], reverse=True)

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
        " &nbsp;&#9632;&nbsp; [`Google Scholar`](https://scholar.google.com/citations?user=4O8TNrgAAAAJ \"Google Scholar\")",
        "",
        f"*{len(papers)} peer-reviewed publications and preprints"
        " &nbsp;&#9632;&nbsp; citations (ADS)"
        " &nbsp;&#9632;&nbsp; h-index (ADS)"
        f" &nbsp;&#9632;&nbsp; {__import__('datetime').date.today().strftime('%B %Y')}*",
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
