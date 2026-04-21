#!/usr/bin/env python3
"""Generate the repositories page for garrethmartin.github.io.

Fetches public, non-forked repositories from GitHub and writes
_posts/2019-04-06-repos.md.
Run from the repo root:  python generate_repos.py

Optionally set a GITHUB_TOKEN env variable to avoid rate-limiting:
  export GITHUB_TOKEN=ghp_...
  python generate_repos.py
"""

import os
import requests

GITHUB_USER = "garrethmartin"
OUT_FILE    = "_posts/2019-04-06-repos.md"


def fetch_repos(user, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    repos, page = [], 1
    while True:
        url    = f"https://api.github.com/users/{user}/repos"
        params = {"type": "public", "per_page": 100, "page": page}
        resp   = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        batch  = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def main():
    token = os.environ.get("GITHUB_TOKEN")
    repos = fetch_repos(GITHUB_USER, token)
    owned = [r for r in repos if not r["fork"]]
    owned.sort(key=lambda r: r["updated_at"], reverse=True)

    print(f"Found {len(owned)} owned public repos (excluded {len(repos) - len(owned)} forks).")

    lines = [
        "---",
        "layout: post",
        "title: Repositories",
        "cover: HzWeb.png",
        "date:   2013-12-04 12:00:00",
        "categories: posts",
        "---",
        "",
        f"Public repositories on [`GitHub`](https://github.com/{GITHUB_USER}) — excluding forks.",
        "",
    ]

    for r in owned:
        name  = r["name"]
        desc  = r["description"] or ""
        url   = r["html_url"]
        detail = desc
        lines.append(f"### [`{name}`]({url})")
        if detail:
            lines.append(detail)
        lines.append("")

    with open(OUT_FILE, "w") as f:
        f.write("\n".join(lines))

    print(f"Written to {OUT_FILE}")


if __name__ == "__main__":
    main()
