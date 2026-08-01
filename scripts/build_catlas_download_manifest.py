#!/usr/bin/env python3
"""Build a file-level manifest for publication-linked CATLAS downloads."""

from __future__ import annotations

import csv
import json
import re
import urllib.parse
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

from multiome_catalog.catalog import classify_file, ena_fastq_files, fetch_bytes, remote_size


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "data/catlas_study_sources.json"
OUTPUT = ROOT / "data/catlas_download_manifest.csv"
FIELDS = [
    "source_record_id", "role", "repository", "accession", "url", "is_direct",
    "file_type", "size_bytes", "size_basis", "count_in_storage", "retrieved_date", "notes",
]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a" and (href := dict(attrs).get("href")):
            self.links.append(href)


def geo_url(accession: str, filename: str) -> str:
    prefix = accession[:-3] + "nnn"
    return (
        f"https://ftp.ncbi.nlm.nih.gov/geo/series/{prefix}/{accession}/suppl/"
        + urllib.parse.quote(filename)
    )


def size_or_zero(url: str) -> tuple[int, str]:
    try:
        return remote_size(url), "exact HTTP Content-Length"
    except Exception as error:
        return 0, f"not exposed ({type(error).__name__})"


def row(record_id: str, role: str, repository: str, accession: str, url: str,
        direct: bool, file_type: str, size: int = 0, basis: str = "not exposed",
        count: bool = False, notes: str = "") -> dict[str, object]:
    return {
        "source_record_id": record_id, "role": role, "repository": repository,
        "accession": accession, "url": url, "is_direct": str(direct).lower(),
        "file_type": file_type, "size_bytes": size, "size_basis": basis,
        "count_in_storage": str(count).lower(), "retrieved_date": date.today().isoformat(),
        "notes": notes,
    }


def fetal_brain_assets() -> list[str]:
    readme = fetch_bytes(
        "https://raw.githubusercontent.com/linnarsson-lab/fetal_brain_multiomics/master/README.md"
    ).decode("utf-8")
    return list(dict.fromkeys(re.findall(r"https://www\.dropbox\.com/[^)\s]+", readme)))


def html_links(url: str) -> list[str]:
    parser = LinkParser()
    parser.feed(fetch_bytes(url).decode("utf-8", errors="replace"))
    return [urllib.parse.urljoin(url, link) for link in parser.links]


def brainscope_assets(pages: list[str]) -> list[str]:
    links: list[str] = []
    for page in pages:
        page_links = html_links(page)
        links.extend(page_links)
        if "atac_fragment_files" in page:
            for link in page_links:
                if "snATAC_fragment_files" in link and link.endswith("/"):
                    links.extend(html_links(link))
    extensions = (".gz", ".tbi", ".bw", ".bigwig", ".bed", ".zip")
    return list(dict.fromkeys(link for link in links if link.lower().split("?", 1)[0].endswith(extensions)))


def build() -> list[dict[str, object]]:
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    output: list[dict[str, object]] = []
    for source in sources:
        record_id = source["source_record_id"]
        for url in source["raw_urls"]:
            output.append(row(record_id, "raw", "repository", "", url, False, "repository landing page"))

        accession = source.get("ena_accession", "")
        if accession:
            for asset in ena_fastq_files(
                accession, source.get("ena_species", ""), set(source.get("ena_strategies", []))
            ):
                output.append(row(
                    record_id, "raw", "ENA", asset["run_accession"], asset["url"], True,
                    "FASTQ", asset["size_bytes"], "exact ENA fastq_bytes", True,
                    asset["library_strategy"],
                ))

        if source.get("nemo_collection"):
            size = source.get("nemo_size_bytes", 0)
            output.append(row(
                record_id, "raw", "NEMO Archive", source["nemo_collection"],
                f"https://assets.nemoarchive.org/{source['nemo_collection']}", False,
                "collection", size, "exact NEMO manifest total" if size else "not exposed",
                bool(size), "Collection landing page; download is packaged by NEMO.",
            ))

        if source.get("ega_dataset"):
            output.append(row(
                record_id, "raw", "EGA", source["ega_dataset"],
                f"https://ega-archive.org/datasets/{source['ega_dataset']}", False, "BAM",
                source["ega_size_bytes"], "exact sum of EGA file metadata", True,
                "Controlled access; authorization is required to download.",
            ))

        for asset in source.get("processed", []):
            url = geo_url(asset["geo"], asset["file"])
            size = asset.get("size_bytes")
            basis = "exact GEO file listing"
            if size is None:
                size, basis = size_or_zero(url)
            output.append(row(
                record_id, "processed", "GEO", asset["geo"], url, True,
                classify_file(asset["file"], url), size, basis, bool(size),
            ))

        pages = source.get("processed_pages", [])
        for url in pages:
            output.append(row(record_id, "processed", "author/repository", "", url, False, "download page"))

        if record_id == "humanbraindev":
            for url in fetal_brain_assets():
                size, basis = size_or_zero(url)
                is_reference = "refdata-cellranger" in url
                output.append(row(
                    record_id, "processed", "Dropbox", "", url, True,
                    classify_file("", url), size, basis, bool(size) and not is_reference,
                    "Cell Ranger reference; excluded from dataset storage." if is_reference else "",
                ))

        if record_id == "humanbrainscope":
            for url in brainscope_assets(pages):
                size, basis = size_or_zero(url)
                if not size:
                    continue
                output.append(row(
                    record_id, "processed", "BrainSCOPE", "", url, True,
                    classify_file("", url), size, basis, bool(size),
                ))
    unique: dict[tuple[str, str, str], dict[str, object]] = {}
    for item in output:
        unique[(str(item["source_record_id"]), str(item["role"]), str(item["url"]))] = item
    return list(unique.values())


def main() -> None:
    rows = build()
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"rows": len(rows), "output": str(OUTPUT)}, indent=2))


if __name__ == "__main__":
    main()
