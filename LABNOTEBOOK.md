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
- Listed CELLxGENE cell counts sum to 27,161,660; primary observations sum to
  16,635,211 because 73 records are wholly derived and four mix primary and
  non-primary observations.
- CELLxGENE directly provides H5AD for all 107 records and fragments for 12.
- The official 10x sitemap contained 784 dataset pages; structured metadata
  classified 23 as Multiome. All 23 provide fragments and BED peaks; 18 provide
  BigWig tracks. Seven do not publish a recovered-nucleus count in page metadata.
- 89 CELLxGENE rows inherit at least one collection-level raw repository link;
  18 have only the processed CELLxGENE asset URL.

### Storage model

For CELLxGENE raw reads, used 9,818,889 bytes per primary cell, based on the 10x
Chromium X PBMC example. Raw bytes are zero on derived records so aggregate storage
does not double-count subsets. This estimate is sensitive to sequencing depth,
read lengths, compression, and failed/removed barcodes, so it is suitable for
capacity planning rather than archive accounting.

### Validation

Required invariants: 107 CELLxGENE rows, 29 CELLxGENE collections, 23 official 10x
rows, no missing tissue/species values, a processed URL for every row, and format
flags consistent with advertised file types. Exact byte totals are summed directly
from provider metadata. URL reachability is checked with HTTP range requests in
the validation script to avoid downloading large assets.

