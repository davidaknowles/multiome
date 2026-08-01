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
