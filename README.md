# Public multiome and scATAC dataset catalog

This repository catalogs public multiome datasets and mammalian single-cell
chromatin-accessibility datasets indexed by CATLAS. The main
machine-readable table is
[`data/public_10x_multiome_datasets.csv`](data/public_10x_multiome_datasets.csv).
The repository also includes a reusable
[`process-scatac-multiome` skill](skills/process-scatac-multiome/SKILL.md) for QC,
processing, and sequence-to-function target preparation.
The filename is retained for compatibility with the original 10x-only catalog. It
contains **312 provider records** retrieved on 2026-08-01:

- 107 CELLxGENE Discover datasets (EFO:0030059), spanning 29 collections,
  27,161,660 provider-listed cells, and 14,309,726 cells specifically labeled
  10x Multiome in the current H5AD files;
- 23 official 10x Genomics example datasets, spanning 126,477 reported nuclei
  plus seven pages where the provider does not report a recovered-nucleus count;
- 14 mammalian CATLAS chromatin-accessibility records: seven human, five mouse,
  one rhesus macaque, and one common marmoset dataset;
- 160 released ENCODE `MultiomicsSeries`: 117 human and 43 mouse, with direct raw
  and processed files from both the chromatin-accessibility and RNA components;
- eight primary GEO studies used by the MiniAtlas work but missing from the
  existing table. The derived MiniAtlas release itself is not included.

The CSV is the complete requested table. It includes tissues, species, cell count,
raw and processed URLs, DOI, portal URL, file-type inventory and boolean columns
for AnnData/H5AD, BigWig, fragment, and BED availability. It also includes raw,
processed, and combined storage in bytes so totals are machine-summable.

## Coverage and interpretation

“Dataset” means a provider catalog record, not necessarily an independent
experiment. CELLxGENE contains many derived cell-type subsets and alternate views;
`primary_cell_count` distinguishes these from primary observations. The catalog
does not claim that every paper using the assay can be found from these
structured public catalogs. It does completely enumerate the current CELLxGENE
10x multiome filter (the expected 107 records) and the current official 10x public
dataset catalog. It also enumerates all released ENCODE `MultiomicsSeries` at the
retrieval date. The CATLAS addition includes records returned for the four
mammalian species when filtering for `snATAC-seq`, `sci-ATAC-seq`, or `10x
multiome`; records may also contain paired snRNA-seq or snm3C-seq.
Provider records can overlap and should not be summed as independent experiments.
GSE196235, already linked from a CELLxGENE record, is not added again as a curated
GEO row.

The curated source registry is
[`data/curated_multiome_source_studies.json`](data/curated_multiome_source_studies.json).
It records the selected GSM pairs and primary BioProject locations. The catalog
builder enumerates the current direct GEO series supplementary files from those
records. Storage for these eight rows is left unknown rather than counting entire
projects that can contain unrelated runs.

CELLxGENE's assay filter operates at dataset-record level. Of its 107 matching
records, 72 contain additional assays. Therefore `cell_count` is the full provider
record size while `multiome_cell_count` is the exact number of observations whose
current H5AD `assay_ontology_term_id` is `EFO:0030059`. Storage modeling uses the
corresponding `multiome_primary_cell_count`, not the larger record total.

CELLxGENE H5AD assets generally contain the RNA representation. ATAC is only
directly downloadable from CELLxGENE when a fragment asset is listed. A collection
level raw-data link may point to GEO, HCA, EGA, Synapse, ArrayExpress, or another
repository and may require registration or controlled-access approval. Blank raw
URL fields mean CELLxGENE did not publish a link, not that raw reads cannot exist.

Although all 14 CATLAS detail pages label their own download products “Coming
Soon,” the original publications point to usable copies in ENA, NEMO Archive,
EGA, dbGaP, GEO, Synapse/PsychENCODE, Dropbox, and author portals. Those links are
now joined into the main catalog. The file-level
[`data/catlas_download_manifest.csv`](data/catlas_download_manifest.csv) contains
1,116 entries, including 1,010 direct ENA FASTQs and 83 direct processed assets.
It distinguishes direct files, repository landing pages, and controlled-access
collections. The CATLAS `cell_count` values remain verbatim because several are
bounds, approximations, or combined ATAC/RNA counts.

## Storage estimates

Processed storage is exact: it is the sum of byte sizes reported by CELLxGENE for
H5AD/fragment/index assets, by 10x for output and summary assets, and by ENCODE for
released component assets. Official 10x and ENCODE raw storage is exact from
listed input/read assets.

CELLxGENE does not expose raw archive sizes consistently. Its raw estimate uses
9,818,889 bytes per primary cell, calibrated from the official 10x 10k PBMC
Chromium X example (107,754,854,400-byte FASTQ archive / 10,974 recovered nuclei).
This is a planning estimate, not a repository measurement. Derived/non-primary
rows receive zero raw bytes to prevent the same experiment being counted again.
The calibration is recorded in [`data/storage_model.csv`](data/storage_model.csv).

Current aggregate storage represented by the table is:

| Source | Raw | Processed | Basis |
|---|---:|---:|---|
| CELLxGENE | 88.119 TB | 0.692 TB | modeled raw; exact hosted assets |
| 10x Genomics | 1.226 TB | 1.218 TB | exact listed assets |
| CATLAS | 22.321 TB | 1.024 TB | exact known publication-linked assets; lower bound |
| GEO source studies | unknown | unknown | direct files linked; sizes not snapshotted |
| ENCODE | 6.263 TB | 14.181 TB | exact released component assets |
| **Known total** | **117.929 TB** | **17.114 TB** | decimal TB; excludes unknown-size controlled/additional assets |

## Rebuild

The builder uses only the Python standard library:

```bash
PYTHONPATH=src python scripts/build_catalog.py
```

Refresh the publication-linked CATLAS file manifest first when repository assets
may have changed:

```bash
PYTHONPATH=src python scripts/build_catlas_download_manifest.py
```

Use `--cellxgene-only` to rebuild only the 107 CELLxGENE rows, or
`--exclude-catlas`, `--exclude-encode`, or `--exclude-curated-sources` to omit an
extension. The source endpoints are
the [CELLxGENE Discover API](https://api.cellxgene.cziscience.com/curation/ui/),
the [10x Genomics dataset catalog](https://www.10xgenomics.com/datasets), and the
[CATLAS browse catalog](https://www.catlas.org/catlas/browse.php),
[ENCODE released multiomics search](https://www.encodeproject.org/search/?type=MultiomicsSeries&status=released),
and [NCBI GEO](https://www.ncbi.nlm.nih.gov/geo/).

Assay-specific counts are version-pinned in
[`data/cellxgene_h5ad_assay_counts_2026-08-01.csv`](data/cellxgene_h5ad_assay_counts_2026-08-01.csv).
If CELLxGENE revises a dataset, the main builder stops instead of silently using a
stale count. Refresh the snapshot with `scripts/extract_cellxgene_assay_counts.py`;
that maintenance command additionally requires `h5py` and `fsspec` and reads only
H5AD observation metadata with HTTP range requests.

## Column dictionary

| Column | Meaning |
|---|---|
| `source_record_id` | CELLxGENE UUID, 10x slug, CATLAS `DataID`, GEO `GSE`, or ENCODE `ENCSR` |
| `collection_id` | CELLxGENE collection UUID; blank for other providers |
| `cell_count` | Provider-reported cells/nuclei; `not reported` if absent |
| `primary_cell_count` | CELLxGENE non-derived observations; equal to cell count for 10x examples; unavailable from CATLAS |
| `multiome_cell_count` | Cells specifically assigned to 10x Multiome; exact from current H5AD metadata |
| `multiome_primary_cell_count` | Non-derived Multiome cells used for raw-storage modeling |
| `raw_data_urls` | Raw repository landing pages or direct input assets |
| `raw_data_status` | Whether a raw repository/input link was found |
| `processed_data_urls` | Direct assets and, where files are enumerated on demand, download pages |
| `other_data_urls` | Auxiliary data portals (for example Figshare, Zenodo, or Single Cell Portal) |
| `available_file_types` | All types directly advertised for the row |
| `has_*` | Requested format flags; H5AD counts as AnnData |
| `*_storage_bytes` | Integer byte totals suitable for known-size aggregation; unknown and overlapping assets are excluded with an explicit basis |
| `*_storage_basis` | Exact versus modeled provenance |
| `access` | Public metadata/assets; linked repositories can impose access controls |
