# QC and processing

## Interpret QC jointly

Compute metrics per capture with one pinned annotation. TSS enrichment definitions
differ across tools, so do not compare values without checking implementation.
Use thresholds to identify technical failure, not to improve cluster separation.

### Library metrics

- Q30, barcode validity, saturation, and read depth;
- proper MAPQ-filtered pairs, unmapped/chimeric/non-primary fractions;
- duplicates, unique nuclear fragments, and complexity;
- TSS profile, fragment-size periodicity, FRiP, and blacklist signal;
- barcode-rank curve, called cells, and fragments assigned to cells;
- depth-normalized agreement between biological replicates.

Use Cell Ranger ARC reports for 10x libraries and import `summary.csv` into pandas.
Use MultiQC to collect sequencing/alignment reports. ENCODE bulk FRiP guidance
(>0.3 good; >0.2 acceptable) is a library diagnostic, not a single-cell gate.

### Cell metrics

Use SnapATAC2 to calculate unique fragments and TSS enrichment. Add FRiP,
blacklist, mitochondrial/non-primary fraction, nucleosome signal, and doublet
score to `adata.obs`. Plot joint distributions by library with plotnine.

SnapATAC2 defaults of at least 1,000 fragments and TSS enrichment 5 are useful
starting anchors. Depending on tissue and chemistry, inspect ranges such as
1,000–5,000 fragments, TSS enrichment 4–10, and FRiP 0.15–0.30. Derive actual
boundaries from each library and check upper depth tails for doublets. Do not move
numeric cutoffs between TSS implementations.

### Multiome checks

Store ATAC and RNA in MuData without independently filtering and silently
intersecting barcodes. Use Scanpy for RNA counts, genes, mitochondrial/ribosomal
fractions, and Scrublet scores. Review joint-good, ATAC-low, RNA-low, and joint-low
states before removal; genuine cell types can be weak in one modality. Treat ATAC
gene activity as annotation support, not measured expression or regulatory proof.

### Peaks and matrices

Use genome tiles for initial structure, then pseudobulk fragments by sample and
broad cell state. Require enough cells/fragments, call peaks with MACS3 paired
fragment mode, and preserve summit and pseudobulk provenance. Create a fixed-width
or otherwise documented non-overlapping consensus with bioframe/PyRanges. Exclude
blacklists and poor mappability, then quantify all cells in the frozen regions.

Keep raw scipy sparse counts. Write derivatives to separate AnnData layers and
large tables/tracks to Parquet, Zarr, or BigWig. Check replicate concordance before
pooling.

## Report

Provide metric distributions before/after filtering, retention by donor/capture,
threshold rationale, doublet and modality-discordance calls, replicate agreement,
depth/quality effects on embeddings, file checksums, commands, environments, and
all exclusions.
