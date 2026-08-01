# Public 10x Multiome dataset catalog

This repository catalogs public 10x Multiome ATAC + Gene Expression datasets. The
main machine-readable table is
[`data/public_10x_multiome_datasets.csv`](data/public_10x_multiome_datasets.csv).
It contains **130 records** retrieved on 2026-08-01:

- 107 CELLxGENE Discover datasets (EFO:0030059), spanning 29 collections and
  27,161,660 listed cells;
- 23 official 10x Genomics example datasets, spanning 126,477 reported nuclei
  plus seven pages where the provider does not report a recovered-nucleus count.

The CSV is the complete requested table. It includes tissues, species, cell count,
raw and processed URLs, DOI, portal URL, file-type inventory and boolean columns
for AnnData/H5AD, BigWig, fragment, and BED availability. It also includes raw,
processed, and combined storage in bytes so totals are machine-summable.

## Coverage and interpretation

“Dataset” means a provider catalog record, not necessarily an independent
experiment. CELLxGENE contains many derived cell-type subsets and alternate views;
`primary_cell_count` distinguishes these from primary observations. The catalog
does not claim that every paper using the assay can be found from these two
structured public catalogs. It does completely enumerate the current CELLxGENE
10x multiome filter (the expected 107 records) and the current official 10x public
dataset catalog.

CELLxGENE H5AD assets generally contain the RNA representation. ATAC is only
directly downloadable from CELLxGENE when a fragment asset is listed. A collection
level raw-data link may point to GEO, HCA, EGA, Synapse, ArrayExpress, or another
repository and may require registration or controlled-access approval. Blank raw
URL fields mean CELLxGENE did not publish a link, not that raw reads cannot exist.

## Storage estimates

Processed storage is exact: it is the sum of byte sizes reported by CELLxGENE for
H5AD/fragment/index assets or by 10x for all output and summary assets. Official
10x raw storage is also exact from listed input assets.

CELLxGENE does not expose raw archive sizes consistently. Its raw estimate uses
9,818,889 bytes per primary cell, calibrated from the official 10x 10k PBMC
Chromium X example (107,754,854,400-byte FASTQ archive / 10,974 recovered nuclei).
This is a planning estimate, not a repository measurement. Derived/non-primary
rows receive zero raw bytes to prevent the same experiment being counted again.
The calibration is recorded in [`data/storage_model.csv`](data/storage_model.csv).

Current aggregate storage represented by the table is:

| Source | Raw | Processed | Basis |
|---|---:|---:|---|
| CELLxGENE | 163.34 TB | 0.692 TB | modeled raw; exact hosted assets |
| 10x Genomics | 1.226 TB | 1.218 TB | exact listed assets |
| **Total** | **164.57 TB** | **1.909 TB** | decimal TB |

## Rebuild

The builder uses only the Python standard library:

```bash
PYTHONPATH=src python scripts/build_catalog.py
```

Use `--cellxgene-only` to rebuild only the 107 CELLxGENE rows. The source endpoints
are the [CELLxGENE Discover API](https://api.cellxgene.cziscience.com/curation/ui/)
and the [10x Genomics dataset catalog](https://www.10xgenomics.com/datasets).

## Column dictionary

| Column | Meaning |
|---|---|
| `source_record_id` | Stable CELLxGENE dataset UUID or 10x page slug |
| `collection_id` | CELLxGENE collection UUID; blank for 10x examples |
| `cell_count` | Provider-reported cells/nuclei; `not reported` if absent |
| `primary_cell_count` | CELLxGENE non-derived observations; equal to cell count for 10x examples |
| `raw_data_urls` | Raw repository landing pages or direct input assets |
| `processed_data_urls` | Direct downloadable provider assets |
| `available_file_types` | All types directly advertised for the row |
| `has_*` | Requested format flags; H5AD counts as AnnData |
| `*_storage_bytes` | Integer byte totals suitable for aggregation |
| `*_storage_basis` | Exact versus modeled provenance |
| `access` | Public metadata/assets; linked repositories can impose access controls |

