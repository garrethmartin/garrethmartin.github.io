#!/usr/bin/env python3
"""Regenerate publication_list.docx from ADS + Scholar, convert to PDF via OnlyOffice,
and copy both CV_Martin.pdf and publication_list.pdf into the website files/ dir.

Run from the repo root:  python sync_cv_files.py
Requires OnlyOffice Desktop Editors (snap) for DOCX→PDF conversion.
"""

import glob
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT         = os.path.dirname(os.path.abspath(__file__))
CV_STUFF_DIR = os.path.expanduser("~/Code/CV_stuff")
ADS_TOKEN    = "7rbhCKGe8EGuSLM3XpV2RZ1v5RpjvnOqUgb13X7i"
LIBRARY_ID   = "nThU2Yw3SUytqSYjksZ8uA"
SCHOLAR_ID   = "4O8TNrgAAAAJ"
FILES_DIR    = os.path.join(ROOT, "files")

sys.path.insert(0, CV_STUFF_DIR)
from ads_publist_builder import fetch_library_papers, build_publication_docx, normalize_title

CUSTOM_PAPERS = [
    {
        "title": "Intracluster light and dark matter halo shapes reflect common assembly, not mutual coupling: shape correspondence in CDM but not SIDM",
        "authors": [
            "Martin, G.",
            "Hatch, N. A.",
            "Cui, W.",
            "Fernandez, A.",
            "Bahé, Y. M.",
            "Fischer, M. S.",
            "Montes, M.",
            "Pearce, F. R.",
            "Sabiu, C. G.",
            "Yepes, G.",
            "Yoo, J.",
        ],
        "year": 2026,
        "month": 8,
        "journal": "MNRAS",
        "pub_note": "submitted",
        "link_url": "https://garrethmartin.github.io/files/DM_vs_ICL_shapes.pdf",
        "link_text": "PDF link",
        "starred": False,
    }
]

CUSTOM_BOOKS = [
    {
        "title": "From Dark Matter to Machine Learning: A collection of EAS 2022 proceedings from the S3 and S11 symposia",
        "authors": [
            "Tortora, C.",
            "Brescia, M.",
            "Napolitano, N. R.",
            "Chamba, N.",
            "Lazar, I.",
            "Martin, G. W.",
            "Palomares-Ruiz, S.",
        ],
        "year": 2023,
        "month": 0,
        "journal": "MemSAIT",
        "volume": "Vol. 94, n. 3",
        "pub_note": "Co-Editor",
        "link_url": "https://www.memsait.it/volumi/MemSAIT-vol94-n3-2023.php",
        "link_text": "Table of Contents",
        "starred": False,
    }
]

STARRED_TITLES = {
    "AGN in massive galaxies identified via optical broadband variability: lessons from VST-COSMOS for future LSST science",
    "Investigating the imprints of tidal features on simulated galaxy outskirts in LSST-like mock observations",
    "The dwarf stellar mass function in different environments and the lack of a generic missing dwarfs problem in ΛCDM",
    "Tidal features around simulated groups and cluster galaxies: enhancement and suppression of merger events through environment in LSST-like mock observations",
    "Intracluster light is a biased tracer of the dark matter distribution in clusters",
    "New tools for studying planarity in galaxy satellite systems: Milky Way satellite planes are consistent with ΛCDM",
    "The structural properties of nearby dwarf galaxies in low-density environments — size, surface brightness, and colour gradients",
    "Assembly of the intracluster light in the HORIZON-AGN simulation",
    "The properties of AGN in dwarf galaxies identified via SED fitting",
    "Characterizing tidal features around galaxies in cosmological simulations",
    "The morphological mix of dwarf galaxies in the nearby Universe",
    "Relaxed blue ellipticals: accretion-driven stellar growth is a key evolutionary channel for low mass elliptical galaxies",
    "Extremely massive disc galaxies in the nearby Universe form through gas-rich minor mergers",
    "How the spectral energy distribution and galaxy morphology constrain each other, with application to morphological selection using galaxy colours",
    "Dark matter-deficient dwarf galaxies form via tidal stripping of dark matter in interactions with massive companions",
    "The origin of low-surface-brightness galaxies in the dwarf regime",
    "Why do extremely massive disc galaxies exist today?",
    "When galaxies align: intrinsic alignments of the progenitors of elliptical galaxies in the Horizon-AGN simulation",
}


def get_scholar_data(cache_path):
    try:
        from scholarly import scholarly as _scholarly
        print("  Fetching from Google Scholar live…")
        author = _scholarly.search_author_id(SCHOLAR_ID)
        author = _scholarly.fill(author, sections=["basics", "indices", "publications"])
        pubs = []
        for pub in author.get("publications", []):
            bib = pub.get("bib", {})
            pubs.append({
                "title":         bib.get("title", ""),
                "year":          str(bib.get("pub_year", "")),
                "num_citations": pub.get("num_citations", 0),
            })
        data = {
            "fetched_at":     __import__("datetime").datetime.now().isoformat(),
            "name":           author.get("name", ""),
            "citedby":        author.get("citedby", 0),
            "hindex":         author.get("hindex", 0),
            "i10index":       author.get("i10index", 0),
            "cites_per_year": author.get("cites_per_year", {}),
            "publications":   pubs,
        }
        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Cache updated.")
    except Exception as e:
        print(f"  [ FALLBACK ] Scholar live fetch failed ({e}); reading cache")
        with open(cache_path) as f:
            data = json.load(f)
    citations = {}
    for pub in data.get("publications", []):
        k = normalize_title(pub.get("title", ""))
        if k:
            citations[k] = pub.get("num_citations", 0)
    return data, citations


def docx_to_pdf_onlyoffice(docx_path):
    docx_path = pathlib.Path(docx_path).resolve()
    home = pathlib.Path.home()

    converter_dirs = sorted(
        glob.glob(
            "/snap/onlyoffice-desktopeditors/*/opt/onlyoffice/desktopeditors/converter"
        ),
        reverse=True,
    )
    allfonts_files = sorted(
        glob.glob(
            str(
                home
                / "snap/onlyoffice-desktopeditors/*/.local/share/onlyoffice/desktopeditors/data/fonts/AllFonts.js"
            )
        ),
        reverse=True,
    )

    if not converter_dirs:
        raise RuntimeError("OnlyOffice snap not found — install via: snap install onlyoffice-desktopeditors")
    if not allfonts_files:
        raise RuntimeError("AllFonts.js not found — open OnlyOffice once to generate it")

    converter_dir = pathlib.Path(converter_dirs[0])
    x2t = converter_dir / "x2t"
    pdf_path = docx_path.with_suffix(".pdf")

    params_xml = f"""<TaskQueueDataConvert>
  <m_sFileFrom>{docx_path}</m_sFileFrom>
  <m_sFileTo>{pdf_path}</m_sFileTo>
  <m_nFormatTo>513</m_nFormatTo>
  <m_sFontDir>/usr/share/fonts</m_sFontDir>
  <m_sAllFontsPath>{allfonts_files[0]}</m_sAllFontsPath>
</TaskQueueDataConvert>"""

    params_file = pathlib.Path("/tmp/x2t_publist_params.xml")
    params_file.write_text(params_xml)

    subprocess.run([str(x2t), str(params_file)], cwd=str(converter_dir), check=True)
    return pdf_path


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

    print("Fetching Google Scholar data…")
    scholar_data, scholar_citations = get_scholar_data(
        os.path.join(CV_STUFF_DIR, "scholar_cache.json")
    )
    CITATIONS = f"{scholar_data['citedby']:,}"
    H_INDEX   = str(scholar_data["hindex"])
    print(
        f"  Scholar stats (fetched {scholar_data['fetched_at'][:10]}): "
        f"{CITATIONS} citations, h-index {H_INDEX}, {len(scholar_citations)} papers indexed"
    )

    print("Fetching papers from ADS…")
    papers, num_found, num_docs = fetch_library_papers(ADS_TOKEN, LIBRARY_ID)
    print(f"  {num_found} found, {len(papers)} returned")

    # Merge with ADS citation counts — use whichever source is larger per paper
    for p in papers:
        title_raw = (p.get("title") or [""])[0]
        ads_count = int(p.get("citation_count") or 0)
        if title_raw and ads_count:
            k = normalize_title(title_raw)
            if k:
                scholar_citations[k] = max(scholar_citations.get(k, 0), ads_count)

    out_docx = os.path.join(CV_STUFF_DIR, "publication_list.docx")
    print(f"Generating {os.path.basename(out_docx)}…")
    result = build_publication_docx(
        papers=papers,
        custom_papers=CUSTOM_PAPERS,
        custom_books=CUSTOM_BOOKS,
        starred_titles=STARRED_TITLES,
        author_name="Garreth Martin",
        target_author="Martin, G",
        citations=CITATIONS,
        h_index=H_INDEX,
        output_path=out_docx,
        use_initials=True,
        max_authors=8,
        show_talks=False,
        scholar_citations=scholar_citations,
    )
    print(f"  {result['num_papers']} papers — saved to {out_docx}")

    print("Converting to PDF via OnlyOffice…")
    pdf_path = docx_to_pdf_onlyoffice(out_docx)
    print(f"  PDF written: {pdf_path}")

    print("Copying PDFs to files/…")
    copy_pdf("publication_list.pdf", CV_STUFF_DIR, FILES_DIR)
    copy_pdf("CV_Martin.pdf", CV_STUFF_DIR, FILES_DIR)

    print("Done.")


if __name__ == "__main__":
    main()
