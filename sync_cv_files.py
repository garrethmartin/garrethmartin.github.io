#!/usr/bin/env python3
"""Regenerate publication_list.docx from ADS + Scholar, convert to PDF,
and copy both CV_Martin.pdf and publication_list.pdf into the website files/ dir.

Run from the repo root:  python sync_cv_files.py
Requires LibreOffice for DOCX→PDF conversion (libreoffice --headless).
"""

import json
import os
import shutil
import subprocess
import sys

ROOT         = os.path.dirname(os.path.abspath(__file__))
CV_STUFF_DIR = "/home/ppzgm/Code/CV_stuff"
ADS_TOKEN    = "7rbhCKGe8EGuSLM3XpV2RZ1v5RpjvnOqUgb13X7i"
LIBRARY_ID   = "nThU2Yw3SUytqSYjksZ8uA"
FILES_DIR    = os.path.join(ROOT, "files")

sys.path.insert(0, CV_STUFF_DIR)
from ads_publist_builder import fetch_library_papers, build_publication_docx, normalize_title


def load_scholar_cache(path):
    with open(path) as f:
        data = json.load(f)
    citations = {
        normalize_title(p["title"]): p["num_citations"]
        for p in data.get("publications", [])
        if p.get("num_citations", 0) > 0
    }
    return data, citations


def convert_docx_to_pdf(docx_path, out_dir):
    try:
        result = subprocess.run(
            ["libreoffice", "--headless", "--convert-to", "pdf",
             "--outdir", out_dir, docx_path],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            pdf_path = os.path.join(
                out_dir,
                os.path.splitext(os.path.basename(docx_path))[0] + ".pdf",
            )
            print(f"  Converted {os.path.basename(docx_path)} → {os.path.basename(pdf_path)}")
            return pdf_path
        else:
            print(f"  WARNING: LibreOffice exited {result.returncode}: {result.stderr.strip()}")
    except FileNotFoundError:
        print("  WARNING: LibreOffice not found; skipping DOCX→PDF conversion")
    except subprocess.TimeoutExpired:
        print("  WARNING: LibreOffice timed out; skipping conversion")
    return None


def copy_pdf(src_name, src_dir, dst_dir):
    src = os.path.join(src_dir, src_name)
    dst = os.path.join(dst_dir, src_name)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        size_kb = os.path.getsize(dst) // 1024
        print(f"  Copied {src_name} ({size_kb} KB) → files/")
    else:
        print(f"  WARNING: {src} not found; skipping")


def main():
    os.makedirs(FILES_DIR, exist_ok=True)

    print("Loading Google Scholar cache…")
    scholar_data, scholar_citations = load_scholar_cache(
        os.path.join(CV_STUFF_DIR, "scholar_cache.json")
    )
    print(f"  {len(scholar_citations)} papers with Scholar citation data")

    print("Fetching papers from ADS…")
    papers, num_found, num_docs = fetch_library_papers(ADS_TOKEN, LIBRARY_ID)
    print(f"  {num_found} found, {len(papers)} returned")

    out_docx = os.path.join(CV_STUFF_DIR, "publication_list.docx")
    print(f"Generating {os.path.basename(out_docx)}…")
    build_publication_docx(
        papers,
        author_name="Garreth Martin",
        target_author="Martin, G",
        citations=scholar_data.get("citedby", 0),
        h_index=scholar_data.get("hindex", 0),
        output_path=out_docx,
        scholar_citations=scholar_citations,
    )
    print(f"  Written to {out_docx}")

    print("Converting to PDF…")
    convert_docx_to_pdf(out_docx, CV_STUFF_DIR)

    print("Copying PDFs to files/…")
    copy_pdf("publication_list.pdf", CV_STUFF_DIR, FILES_DIR)
    copy_pdf("CV_Martin.pdf", CV_STUFF_DIR, FILES_DIR)

    print("Done.")


if __name__ == "__main__":
    main()
