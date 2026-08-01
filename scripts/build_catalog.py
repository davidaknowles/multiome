#!/usr/bin/env python3
"""Build CSV tables from live CELLxGENE and 10x Genomics metadata."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from multiome_catalog.catalog import (
    RAW_BYTES_PER_PRIMARY_CELL,
    cellxgene_multiome,
    classify_file,
    labels,
    tenx_files,
    tenx_multiome,
)


FIELDNAMES = [
    "source", "source_record_id", "collection_id", "collection_title", "dataset_title",
    "tissues", "species", "cell_count", "primary_cell_count", "doi", "portal_url",
    "raw_data_urls", "processed_data_urls", "available_file_types", "has_adata",
    "has_bigwig", "has_fragments", "has_bed", "raw_storage_bytes", "raw_storage_basis",
    "processed_storage_bytes", "processed_storage_basis", "total_storage_bytes",
    "access", "retrieved_date",
]


def joined_urls(assets: list[dict], role: str | None = None) -> str:
    return "; ".join(
        asset["url"] for asset in assets if role is None or asset.get("role") == role
    )


def flags(filetypes: set[str]) -> dict[str, str]:
    lowered = {value.lower() for value in filetypes}
    return {
        "has_adata": str(bool(lowered & {"h5ad", "adata"})).lower(),
        "has_bigwig": str("bigwig" in lowered).lower(),
        "has_fragments": str("fragment" in lowered).lower(),
        "has_bed": str("bed" in lowered).lower(),
    }


def cellxgene_rows() -> list[dict[str, object]]:
    datasets, collections = cellxgene_multiome()
    rows = []
    today = date.today().isoformat()
    for dataset in datasets:
        collection = collections[dataset["collection_id"]]
        raw_links = [link["link_url"] for link in collection.get("links", []) if link["link_type"] == "RAW_DATA"]
        assets = dataset.get("assets", [])
        filetypes = {
            {"ATAC_FRAGMENT": "fragment", "ATAC_INDEX": "fragment_index"}.get(
                asset["filetype"], asset["filetype"]
            )
            for asset in assets
        }
        primary_cells = dataset.get("primary_cell_count", 0)
        raw_bytes = round(primary_cells * RAW_BYTES_PER_PRIMARY_CELL) if primary_cells else 0
        processed_bytes = sum(asset.get("filesize", 0) for asset in assets)
        row = {
            "source": "CELLxGENE Discover", "source_record_id": dataset["dataset_id"],
            "collection_id": dataset["collection_id"], "collection_title": dataset["collection_name"],
            "dataset_title": dataset["title"], "tissues": labels(dataset.get("tissue", [])),
            "species": labels(dataset.get("organism", [])), "cell_count": dataset["cell_count"],
            "primary_cell_count": primary_cells, "doi": dataset.get("collection_doi") or "",
            "portal_url": f"https://cellxgene.cziscience.com/collections/{dataset['collection_id']}",
            "raw_data_urls": "; ".join(raw_links),
            "processed_data_urls": "; ".join(asset["url"] for asset in assets),
            "available_file_types": "; ".join(sorted(filetypes)),
            "raw_storage_bytes": raw_bytes,
            "raw_storage_basis": (
                "modeled from 9.82 MB/primary cell; primary row" if raw_bytes
                else "0: derived/non-primary row (avoids duplicate raw-data accounting)"
            ),
            "processed_storage_bytes": processed_bytes,
            "processed_storage_basis": "exact sum of CELLxGENE asset sizes",
            "total_storage_bytes": raw_bytes + processed_bytes,
            "access": "public" if raw_links or assets else "metadata only", "retrieved_date": today,
        }
        row.update(flags(filetypes))
        rows.append(row)
    return rows


def tenx_rows() -> list[dict[str, object]]:
    rows = []
    today = date.today().isoformat()
    for portal_url, page in tenx_multiome():
        dataset = page["dataset"]
        assets = tenx_files(page)
        for asset in assets:
            asset["filetype"] = classify_file(asset.get("title", ""), asset["url"])
        raw_assets = [asset for asset in assets if asset["role"] == "raw"]
        processed_assets = [asset for asset in assets if asset["role"] == "processed"]
        filetypes = {asset["filetype"] for asset in assets}
        raw_bytes = sum(asset.get("bytes", 0) for asset in raw_assets)
        processed_bytes = sum(asset.get("bytes", 0) for asset in processed_assets)
        row = {
            "source": "10x Genomics", "source_record_id": dataset["slug"], "collection_id": "",
            "collection_title": "10x Genomics public datasets", "dataset_title": dataset["title"],
            "tissues": "; ".join(dataset.get("anatomicalEntities", [])),
            "species": "; ".join(dataset.get("species", [])),
            "cell_count": dataset.get("cellNucleiCount") or "not reported",
            "primary_cell_count": dataset.get("cellNucleiCount") or "not reported",
            "doi": "", "portal_url": portal_url, "raw_data_urls": joined_urls(raw_assets),
            "processed_data_urls": joined_urls(processed_assets),
            "available_file_types": "; ".join(sorted(filetypes)),
            "raw_storage_bytes": raw_bytes, "raw_storage_basis": "exact sum of 10x input asset sizes",
            "processed_storage_bytes": processed_bytes,
            "processed_storage_basis": "exact sum of 10x output/summary asset sizes",
            "total_storage_bytes": raw_bytes + processed_bytes, "access": "public", "retrieved_date": today,
        }
        row.update(flags(filetypes))
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/public_10x_multiome_datasets.csv"))
    parser.add_argument("--cellxgene-only", action="store_true")
    args = parser.parse_args()
    rows = cellxgene_rows()
    if not args.cellxgene_only:
        rows.extend(tenx_rows())
    write_csv(args.output, rows)
    print(json.dumps({"rows": len(rows), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
