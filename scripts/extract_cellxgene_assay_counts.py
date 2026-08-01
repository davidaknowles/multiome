#!/usr/bin/env python3
"""Extract exact assay-specific counts from current CELLxGENE H5AD assets.

This maintenance script requires h5py and fsspec. It uses HTTP range requests and
reads only obs assay/primary-data columns; expression matrices are not downloaded.
"""

from __future__ import annotations

import argparse
import csv
import multiprocessing as mp
import time
from pathlib import Path

import fsspec
import h5py

from multiome_catalog.catalog import cellxgene_multiome


def extract_one(dataset: dict) -> dict[str, object]:
    url = next(asset["url"] for asset in dataset["assets"] if asset["filetype"] == "H5AD")
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with fsspec.open(url, "rb", block_size=1 << 20, cache_type="readahead").open() as remote:
                with h5py.File(remote, "r") as h5ad:
                    assay = h5ad["obs"]["assay_ontology_term_id"]
                    categories = [
                        value.decode() if isinstance(value, bytes) else str(value)
                        for value in assay["categories"][:]
                    ]
                    codes = assay["codes"][:]
                    mask = codes == categories.index("EFO:0030059")
                    primary = h5ad["obs"]["is_primary_data"][:].astype(bool)
                    return {
                        "dataset_id": dataset["dataset_id"],
                        "dataset_version_id": dataset["dataset_version_id"],
                        "multiome_cell_count": int(mask.sum()),
                        "multiome_primary_cell_count": int((mask & primary).sum()),
                    }
        except Exception as error:
            last_error = error
            time.sleep(1 + attempt)
    raise RuntimeError(f"{dataset['dataset_id']}: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/cellxgene_h5ad_assay_counts_2026-08-01.csv"),
    )
    parser.add_argument("--processes", type=int, default=6)
    args = parser.parse_args()
    datasets, _ = cellxgene_multiome()
    with mp.Pool(args.processes) as pool:
        rows = sorted(pool.map(extract_one, datasets), key=lambda row: row["dataset_id"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
