# Lab notebook

## 2026-08-01 — catalog construction

### Goal and model

Built a reproducible inventory of public 10x Multiome ATAC + Gene Expression
records. A normalized row represents one provider dataset record. CELLxGENE records
are selected using assay ontology `EFO:0030059`; official 10x pages are selected
when the structured page metadata identifies `Epi Multiome` or `Cell Ranger ARC`.

The implementation is split between reusable functions in
`src/multiome_catalog/catalog.py` and the output-specific analysis script
`scripts/build_catalog.py`. No dataset files are downloaded; only metadata and
embedded provider manifests are read.

### Findings

- CELLxGENE returned exactly 107 multiome datasets across 29 collections.
- Listed CELLxGENE record counts sum to 27,161,660, but 72 records mix assays.
  Range-reading the current H5AD observation metadata found 14,309,726 cells
  specifically labeled `EFO:0030059`, of which 8,974,236 are primary.
- CELLxGENE directly provides H5AD for all 107 records and fragments for 12.
- The official 10x sitemap contained 784 dataset pages; structured metadata
  classified 23 as Multiome. All 23 provide fragments and BED peaks; 18 provide
  BigWig tracks. Seven do not publish a recovered-nucleus count in page metadata.
- Publication auditing added the missing iPain accession (GSE253345). Ninety-three
  CELLxGENE rows now inherit at least one raw repository link; 14 have no raw link
  supplied by CELLxGENE or identified in the publication search.

### Storage model

For CELLxGENE raw reads, used 9,818,889 bytes per Multiome primary cell, based on
the 10x Chromium X PBMC example. Raw bytes are zero on derived records so aggregate
storage does not double-count subsets. This corrected the initial all-assay estimate
from 163.34 TB to 88.119 TB. The estimate is sensitive to sequencing depth,
read lengths, compression, and failed/removed barcodes, so it is suitable for
capacity planning rather than archive accounting.

### Validation

Required invariants: 107 CELLxGENE rows, 29 CELLxGENE collections, 23 official 10x
rows, 14,309,726 assay-specific CELLxGENE cells, 8,974,236 primary Multiome cells,
no missing tissue/species values, a processed URL for every row, version-matched
H5AD assay counts, and format flags consistent with advertised file types. Exact
byte totals are summed directly from provider metadata. URL reachability is checked
with HTTP range requests in the validation script to avoid downloading large assets.

## 2026-08-01 — CATLAS mammalian scATAC extension

### Selection and implementation

Added the 14 records returned by CATLAS for the four mammalian species (`Homo
Sapiens`, `Mus musculus`, `Macaca mulatta`, and `Callithrix jacchus`) and the
chromatin-accessibility technologies `snATAC-seq`, `sci-ATAC-seq`, and `10x
multiome`. A second content filter requires “ATAC” or “multiome” in the returned
sequencing label. This retains mixed ATAC/RNA and multiome/snm3C records while
excluding RNA-only, Paired-Tag-only, snm3C-only, and fly records.

Reusable POST retrieval and DOI parsing live in `src/multiome_catalog/catalog.py`;
CATLAS-specific normalization remains in the output builder. Provider spellings,
sample descriptions, sequencing labels, and reported cell-count strings are kept
verbatim. The resulting source breakdown is 107 CELLxGENE, 23 10x Genomics, and
14 CATLAS records.

### Data availability and storage

The CATLAS browse interface advertises a Download action, but each of the 14
resource pages currently marks the prospective products “Coming Soon” and exposes
no direct assets. The new rows therefore contain portal URLs and publication DOIs
but no raw/processed URLs or available-file claims. Storage values are zero only
to preserve integer aggregation; their basis fields state that sizes are unknown,
so aggregate totals exclude CATLAS rather than estimating its data at zero bytes.

### Validation

Added invariants for 14 CATLAS rows, all four mammalian species, DOI and portal
coverage, and the current metadata-only availability state. Unit tests cover DOI
normalization. The full catalog rebuild produces 144 rows while preserving the
previous exact known-size totals.

## 2026-08-01 — CATLAS publication download recovery

### Repository audit

Followed the data-availability statements for all 14 CATLAS publications because
the CATLAS resource pages themselves still show “Coming Soon.” The studies resolve
to ENA/SRA and NEMO for public sequence reads, EGA/dbGaP/PsychENCODE for controlled
human reads, and GEO, Dropbox, BrainSCOPE, or author-hosted directories for
processed matrices, fragments, peaks, and signal tracks. The four-species
neocortex records share study PRJNA953340/GSE229169 but are filtered by species so
raw storage is not duplicated across their catalog rows.

The curated study-to-repository mapping is stored in
`data/catlas_study_sources.json`. Reusable ENA TSV parsing and remote-size lookup
live in the package; dataset-specific enumeration remains in
`scripts/build_catlas_download_manifest.py`. The generated file-level manifest has
1,116 unique record/role/URL entries: 1,010 direct ENA FASTQs, 38 selected GEO
files, 32 BrainSCOPE assets, 13 Dropbox assets, and repository/controlled-access
landing records. No large biological files were downloaded.

### Storage and access findings

Exact known CATLAS assets sum to 22.321 TB raw and 1.024 TB processed. These are
lower bounds: dbGaP and PsychENCODE do not expose public file sizes, the NEMO human
brain collection does not publish a manifest total through its current API, and
legacy author portals contain additional derivative files that would overlap the
selected GEO aggregates. EGA metadata contributes the controlled 7.523 TB human
development BAM collection; its presence in the byte total does not imply public
download access. Rows now state `public`, `controlled raw; public processed`, or a
mixed-access description rather than CATLAS metadata-only access.

### Validation

The rebuilt 144-row catalog requires a raw repository and processed download for
every CATLAS record, positive processed known-size storage for all 14 records, and
raw known-size storage for 12; the two exceptions are dbGaP-only human studies.
The manifest requires unique record/role/URL keys and a positive exact size for
every asset counted toward storage. The full known catalog totals are now 111.666 TB raw and 2.933
TB processed.

## 2026-08-01 — scATAC/multiome processing skill

### Design

Added the repository-owned `process-scatac-multiome` skill. Its core workflow
covers provenance, raw-read and fragment processing, layered library/cell QC,
multiplet detection, multiome pairing, peak construction, annotation, pseudobulk
targets, model-data exports, and hard failure conditions. Detailed guidance is
organized into QC/processing, target-preparation, and primary-source references so
the core skill stays concise.

### Model-facing decisions

The skill treats QC thresholds as sample- and implementation-dependent starting
points rather than universal gates. It preserves raw counts, biological
replicates, and modality-specific failure states. For sequence-to-function work it
prefers insertion profiles or replicate-aware counts over peak labels alone,
requires explicit Tn5-bias evaluation, and separates ATAC and RNA measurement
heads. The revised workflow specifies a Python-first stack: SnapATAC2, Scanpy,
MuData, scvi-tools, MACS3, bioframe/PyRanges, pysam, pyBigWig, scipy/AnnData,
Parquet/Zarr, and plotnine. Cell Ranger remains the preferred chemistry-aware
entry point for 10x FASTQs.

### Validation

Validated the skill frontmatter, name, directory layout, and interface metadata
with the skill-creator validator. After simplification, the skill is 116 lines and
directly routes to three focused reference documents. Sources prioritize current ENCODE, 10x,
SnapATAC2, Signac, and MACS3 documentation plus the ArchR, AMULET, COMPOSITE,
ChromBPNet, scBasset, and Borzoi primary publications.
