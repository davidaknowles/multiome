#!/usr/bin/env python3
"""Validate catalog coverage, schema invariants, totals, and optional URLs."""

from __future__ import annotations

import argparse
import csv
import sys
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def split_urls(value: str) -> list[str]:
    return [url.strip() for url in value.split("; ") if url.strip()]


def check_url(url: str) -> tuple[str, bool, str]:
    last_error: Exception | None = None
    for attempt in range(3):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 multiome-catalog/0.1", "Range": "bytes=0-0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return url, response.status < 400, str(response.status)
        except Exception as error:
            last_error = error
            # Repository landing pages occasionally reject range requests. Try HEAD.
            try:
                head = urllib.request.Request(
                    url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 multiome-catalog/0.1"}
                )
                with urllib.request.urlopen(head, timeout=45) as response:
                    return url, response.status < 400, str(response.status)
            except Exception:
                if attempt < 2:
                    time.sleep(1 + attempt)
    assert last_error is not None
    return url, False, f"{type(last_error).__name__}: {last_error}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path, nargs="?", default=Path("data/public_10x_multiome_datasets.csv"))
    parser.add_argument("--check-urls", action="store_true")
    args = parser.parse_args()
    with args.catalog.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    sources = Counter(row["source"] for row in rows)
    assert len(rows) == 144, len(rows)
    assert sources == {"CELLxGENE Discover": 107, "10x Genomics": 23, "CATLAS": 14}, sources
    cxg = [row for row in rows if row["source"] == "CELLxGENE Discover"]
    assert len({row["collection_id"] for row in cxg}) == 29
    assert sum(int(row["cell_count"]) for row in cxg) == 27_161_660
    assert sum(int(row["primary_cell_count"]) for row in cxg) == 16_635_211
    assert sum(int(row["multiome_cell_count"]) for row in cxg) == 14_309_726
    assert sum(int(row["multiome_primary_cell_count"]) for row in cxg) == 8_974_236
    assert sum(row["is_multiome_only"] == "false" for row in cxg) == 72
    assert sum(not row["raw_data_urls"] for row in cxg) == 14
    assert all(row["tissues"] and row["species"] for row in rows)
    hosted = [row for row in rows if row["source"] != "CATLAS"]
    assert all(row["processed_data_urls"] for row in hosted)
    assert all(int(row["processed_storage_bytes"]) > 0 for row in hosted)
    assert sum(row["has_adata"] == "true" for row in cxg) == 107
    assert sum(row["has_fragments"] == "true" for row in cxg) == 12
    tenx = [row for row in rows if row["source"] == "10x Genomics"]
    assert sum(row["has_fragments"] == "true" for row in tenx) == 23
    assert sum(row["has_bed"] == "true" for row in tenx) == 23
    assert sum(row["has_bigwig"] == "true" for row in tenx) == 18
    assert sum(row["cell_count"] == "not reported" for row in tenx) == 7
    catlas = [row for row in rows if row["source"] == "CATLAS"]
    assert {row["species"] for row in catlas} == {
        "Homo Sapiens", "Mus musculus", "Macaca mulatta", "Callithrix jacchus"
    }
    assert all(row["portal_url"] and row["doi"] for row in catlas)
    assert all(row["raw_data_urls"] and row["processed_data_urls"] for row in catlas)
    assert all(int(row["processed_storage_bytes"]) > 0 for row in catlas)
    assert sum(int(row["raw_storage_bytes"]) > 0 for row in catlas) == 12
    assert sum(row["has_adata"] == "true" for row in catlas) >= 1
    assert sum(row["has_bigwig"] == "true" for row in catlas) >= 5
    assert sum(row["has_fragments"] == "true" for row in catlas) >= 2
    assert sum(row["has_bed"] == "true" for row in catlas) >= 6

    manifest_path = args.catalog.parent / "catlas_download_manifest.csv"
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    assert len(manifest) >= 1_100
    assert len({(row["source_record_id"], row["role"], row["url"]) for row in manifest}) == len(manifest)
    assert all(row["url"] for row in manifest)
    assert not [
        row for row in manifest
        if row["count_in_storage"] == "true" and int(row["size_bytes"]) <= 0
    ]

    print(f"validated {len(rows)} rows: {dict(sources)}")
    print(
        "storage bytes:",
        {
            "raw": sum(int(row["raw_storage_bytes"]) for row in rows),
            "processed": sum(int(row["processed_storage_bytes"]) for row in rows),
        },
    )

    if args.check_urls:
        urls = sorted(
            {
                url
                for row in rows
                for column in ("portal_url", "raw_data_urls", "processed_data_urls", "other_data_urls")
                for url in split_urls(row[column])
                # GEO's FTP HTTP gateway rate-limits concurrent range requests.
                # CATLAS GEO files are size-checked while building the manifest.
                if not url.startswith("https://ftp.ncbi.nlm.nih.gov/geo/")
            }
        )
        # Keep concurrency modest because the NCBI FTP gateway returns transient
        # 503 responses when many GEO range requests arrive together.
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(check_url, urls))
        failures = [result for result in results if not result[1]]
        print(f"checked {len(urls)} unique URLs; {len(failures)} failed")
        for url, _, error in failures:
            print(f"FAIL\t{error}\t{url}")
        if failures:
            sys.exit(1)


if __name__ == "__main__":
    main()
