#!/usr/bin/env python3
"""Build CSV tables from live CELLxGENE, 10x Genomics, and CATLAS metadata."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from multiome_catalog.catalog import (
    CATLAS_RESOURCE,
    RAW_BYTES_PER_PRIMARY_CELL,
    catlas_mammalian_scatac,
    cellxgene_multiome,
    classify_file,
    extract_doi,
    labels,
    tenx_files,
    tenx_multiome,
)


FIELDNAMES = [
    "source", "source_record_id", "collection_id", "collection_title", "dataset_title",
    "tissues", "species", "assays", "is_multiome_only", "cell_count", "primary_cell_count",
    "multiome_cell_count", "multiome_primary_cell_count", "multiome_cell_count_basis",
    "doi", "portal_url", "raw_data_urls", "raw_data_status", "processed_data_urls",
    "other_data_urls", "available_file_types", "has_adata",
    "has_bigwig", "has_fragments", "has_bed", "raw_storage_bytes", "raw_storage_basis",
    "processed_storage_bytes", "processed_storage_basis", "total_storage_bytes",
    "access", "retrieved_date",
]

ROOT = Path(__file__).resolve().parents[1]
ASSAY_COUNT_SNAPSHOT = ROOT / "data/cellxgene_h5ad_assay_counts_2026-08-01.csv"
CURATED_LINKS = ROOT / "data/curated_collection_links.csv"
CATLAS_SOURCES = ROOT / "data/catlas_study_sources.json"
CATLAS_MANIFEST = ROOT / "data/catlas_download_manifest.csv"
AUXILIARY_DATA_HOSTS = (
    "figshare", "zenodo", "registry.opendata.aws", "singlecell.broadinstitute.org",
    "celltype.info", ".cells.ucsc.edu", "assets.nemoarchive.org",
)


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
    with ASSAY_COUNT_SNAPSHOT.open(newline="", encoding="utf-8") as handle:
        assay_counts = {row["dataset_id"]: row for row in csv.DictReader(handle)}
    curated_raw: dict[str, list[str]] = {}
    with CURATED_LINKS.open(newline="", encoding="utf-8") as handle:
        for link in csv.DictReader(handle):
            if link["role"] == "raw":
                curated_raw.setdefault(link["collection_id"], []).append(link["url"])
    rows = []
    today = date.today().isoformat()
    for dataset in datasets:
        collection = collections[dataset["collection_id"]]
        raw_links = [link["link_url"] for link in collection.get("links", []) if link["link_type"] == "RAW_DATA"]
        raw_links.extend(curated_raw.get(dataset["collection_id"], []))
        raw_links = list(dict.fromkeys(raw_links))
        other_links = [
            link["link_url"] for link in collection.get("links", [])
            if link["link_type"] not in {"RAW_DATA", "PROTOCOL"}
            and any(host in link["link_url"].lower() for host in AUXILIARY_DATA_HOSTS)
        ]
        assets = dataset.get("assets", [])
        filetypes = {
            {"ATAC_FRAGMENT": "fragment", "ATAC_INDEX": "fragment_index"}.get(
                asset["filetype"], asset["filetype"]
            )
            for asset in assets
        }
        count_row = assay_counts.get(dataset["dataset_id"])
        if count_row is None or count_row["dataset_version_id"] != dataset["dataset_version_id"]:
            raise RuntimeError(
                f"Assay-count snapshot is missing current version for {dataset['dataset_id']}; "
                "run scripts/extract_cellxgene_assay_counts.py"
            )
        primary_cells = dataset.get("primary_cell_count", 0)
        multiome_cells = int(count_row["multiome_cell_count"])
        multiome_primary_cells = int(count_row["multiome_primary_cell_count"])
        raw_bytes = round(multiome_primary_cells * RAW_BYTES_PER_PRIMARY_CELL) if multiome_primary_cells else 0
        processed_bytes = sum(asset.get("filesize", 0) for asset in assets)
        assay_names = labels(dataset.get("assay", []))
        multiome_only = len(dataset.get("assay", [])) == 1
        row = {
            "source": "CELLxGENE Discover", "source_record_id": dataset["dataset_id"],
            "collection_id": dataset["collection_id"], "collection_title": dataset["collection_name"],
            "dataset_title": dataset["title"], "tissues": labels(dataset.get("tissue", [])),
            "species": labels(dataset.get("organism", [])), "assays": assay_names,
            "is_multiome_only": str(multiome_only).lower(), "cell_count": dataset["cell_count"],
            "primary_cell_count": primary_cells, "multiome_cell_count": multiome_cells,
            "multiome_primary_cell_count": multiome_primary_cells,
            "multiome_cell_count_basis": "exact current H5AD obs assay labels",
            "doi": dataset.get("collection_doi") or "",
            "portal_url": f"https://cellxgene.cziscience.com/collections/{dataset['collection_id']}",
            "raw_data_urls": "; ".join(raw_links),
            "raw_data_status": "collection/repository link supplied" if raw_links else "not supplied by provider or publication",
            "processed_data_urls": "; ".join(asset["url"] for asset in assets),
            "other_data_urls": "; ".join(dict.fromkeys(other_links)),
            "available_file_types": "; ".join(sorted(filetypes)),
            "raw_storage_bytes": raw_bytes,
            "raw_storage_basis": (
                "modeled from 9.82 MB/multiome primary cell" if raw_bytes
                else "0: no multiome primary cells (derived row; avoids duplicate accounting)"
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
            "species": "; ".join(dataset.get("species", [])), "assays": "10x multiome",
            "is_multiome_only": "true",
            "cell_count": dataset.get("cellNucleiCount") or "not reported",
            "primary_cell_count": dataset.get("cellNucleiCount") or "not reported",
            "multiome_cell_count": dataset.get("cellNucleiCount") or "not reported",
            "multiome_primary_cell_count": dataset.get("cellNucleiCount") or "not reported",
            "multiome_cell_count_basis": "provider-reported recovered nuclei",
            "doi": "", "portal_url": portal_url, "raw_data_urls": joined_urls(raw_assets),
            "raw_data_status": "direct FASTQ/input asset supplied",
            "processed_data_urls": joined_urls(processed_assets),
            "other_data_urls": "",
            "available_file_types": "; ".join(sorted(filetypes)),
            "raw_storage_bytes": raw_bytes, "raw_storage_basis": "exact sum of 10x input asset sizes",
            "processed_storage_bytes": processed_bytes,
            "processed_storage_basis": "exact sum of 10x output/summary asset sizes",
            "total_storage_bytes": raw_bytes + processed_bytes, "access": "public", "retrieved_date": today,
        }
        row.update(flags(filetypes))
        rows.append(row)
    return rows


def catlas_rows() -> list[dict[str, object]]:
    """Normalize CATLAS records and join publication-linked download assets."""
    sources = {
        item["source_record_id"]: item
        for item in json.loads(CATLAS_SOURCES.read_text(encoding="utf-8"))
    }
    manifest: dict[str, list[dict[str, str]]] = {}
    with CATLAS_MANIFEST.open(newline="", encoding="utf-8") as handle:
        for asset in csv.DictReader(handle):
            manifest.setdefault(asset["source_record_id"], []).append(asset)
    rows = []
    today = date.today().isoformat()
    for dataset in catlas_mammalian_scatac():
        source = sources[dataset["DataID"]]
        assets = manifest[dataset["DataID"]]
        assay = dataset["Sequencing"]
        reported_cells = dataset["CellCount"]
        multiome_only = assay.lower() == "10x multiome"
        exact_multiome_cells = (
            reported_cells.replace(",", "")
            if multiome_only and reported_cells.replace(",", "").isdigit()
            else "not reported"
        )
        filetypes = set(source["file_types"])
        filetypes.update(
            asset["file_type"] for asset in assets
            if asset["is_direct"] == "true" and asset["file_type"]
        )
        raw_bytes = sum(
            int(asset["size_bytes"]) for asset in assets
            if asset["role"] == "raw" and asset["count_in_storage"] == "true"
        )
        processed_bytes = source["processed_size_bytes"]
        processed_urls = [
            asset["url"] for asset in assets
            if asset["role"] == "processed" and asset["is_direct"] == "true"
        ]
        processed_urls.extend(source.get("processed_pages", []))
        row = {
            "source": "CATLAS",
            "source_record_id": dataset["DataID"],
            "collection_id": "",
            "collection_title": "CATLAS mammalian scATAC datasets",
            "dataset_title": dataset["DataName"],
            "tissues": dataset["SampleInfo"],
            "species": dataset["Species"],
            "assays": assay,
            "is_multiome_only": str(multiome_only).lower(),
            "cell_count": reported_cells,
            "primary_cell_count": "not reported",
            "multiome_cell_count": exact_multiome_cells,
            "multiome_primary_cell_count": "not reported",
            "multiome_cell_count_basis": (
                "provider-reported paired multiome nuclei"
                if multiome_only
                else "not applicable or not separable from mixed modalities"
            ),
            "doi": extract_doi(dataset.get("Article", "")),
            "portal_url": CATLAS_RESOURCE.format(dataset_id=dataset["DataID"]),
            "raw_data_urls": "; ".join(source["raw_urls"]),
            "raw_data_status": "publication-linked repository located",
            "processed_data_urls": "; ".join(dict.fromkeys(processed_urls)),
            "other_data_urls": "; ".join(source.get("other_urls", [])),
            "available_file_types": "; ".join(sorted(filetypes)),
            "raw_storage_bytes": raw_bytes,
            "raw_storage_basis": "exact known repository assets; zero excludes controlled/unknown-size assets" if raw_bytes else "not exposed by controlled repository",
            "processed_storage_bytes": processed_bytes,
            "processed_storage_basis": "exact known direct assets; lower bound when repositories expose additional files",
            "total_storage_bytes": raw_bytes + processed_bytes,
            "access": source["access"],
            "retrieved_date": today,
        }
        row.update(flags(filetypes))
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=FIELDNAMES, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/public_10x_multiome_datasets.csv"))
    parser.add_argument("--cellxgene-only", action="store_true")
    parser.add_argument("--exclude-catlas", action="store_true")
    args = parser.parse_args()
    rows = cellxgene_rows()
    if not args.cellxgene_only:
        rows.extend(tenx_rows())
        if not args.exclude_catlas:
            rows.extend(catlas_rows())
    write_csv(args.output, rows)
    print(json.dumps({"rows": len(rows), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
