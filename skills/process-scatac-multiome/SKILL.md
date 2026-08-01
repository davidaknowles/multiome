---
name: process-scatac-multiome
description: Design, implement, review, or troubleshoot reproducible scATAC-seq, snATAC-seq, and paired RNA+ATAC multiome processing, including raw-read processing, QC, doublet removal, peak and count construction, annotation, pseudobulks, and sequence-to-function target preparation. Use for FASTQ, BAM/CRAM, fragments.tsv.gz, BED, sparse matrix, H5, H5AD, or MuData workflows. Prefer Python tools for downstream analysis.
---

# Process scATAC and Multiome

Produce analysis- and model-ready data while preserving sample identity, raw
counts, replicates, technical covariates, and provenance.

## Use this toolchain

Prefer Python unless a chemistry-aware or established external tool is stronger.

| Task | Preferred tool |
|---|---|
| Workflow | Snakemake; pinned conda environments or containers |
| 10x FASTQ processing | Cell Ranger ATAC/ARC, then import outputs into Python |
| ATAC fragments, QC, embedding | SnapATAC2 |
| RNA QC and analysis | Scanpy; Scrublet for RNA doublets |
| Paired data container | MuData with AnnData per modality |
| Joint latent model, if needed | scvi-tools MULTIVI |
| Peak calling | MACS3 in paired-end `BAMPE`, `BEDPE`, or `FRAG` mode |
| Genomic intervals | bioframe or PyRanges |
| BAM/FASTA/tabix access | pysam; pyfaidx when convenient |
| Sparse data and tables | scipy.sparse, pandas/Polars, PyArrow/Parquet, Zarr |
| Signal tracks | pyBigWig |
| QC plots | plotnine |
| Accessibility model targets | ChromBPNet preprocessing conventions |

Use samtools, bgzip/tabix, bedtools, FastQC/MultiQC, and AMULET where their
specialized behavior is needed. Do not reimplement validated file-format or
alignment operations in custom Python.

## Record the data contract

Record donor, specimen, capture, tissue, condition, chemistry, read structure,
reference assembly, annotation, blacklist, raw accession, checksum, software
version, parameters, and barcode namespace. Keep these identifiers attached to
every fragment and cell. Never merge captures before they can be traced back.

## Process the available input

- **FASTQ:** run Cell Ranger ATAC/ARC for 10x data. For other assays, use the
  assay's barcode-aware pipeline and document aligner, duplicate, MAPQ, and Tn5
  conventions. Process libraries independently.
- **BAM/CRAM:** verify assembly, contigs, paired reads, barcode tags, duplicate
  policy, MAPQ, and whether Tn5 offsets were already applied.
- **Fragments:** verify sorted zero-based half-open coordinates, tabix index,
  multiplicity, barcodes, assembly, and duplicate handling.
- **Matrix/H5AD only:** state that fragment-derived QC, peak reconstruction, and
  base-resolution targets are unavailable.

Preserve raw fragments. Write filtered fragments, matrices, peaks, tracks, and
metadata as separate versioned products.

## Run QC per library

1. Review read quality, barcode validity, mapping, duplicates, mitochondrial and
   non-primary reads, library complexity, fragment periodicity, TSS aggregate,
   barcode rank, and signal in peaks or regulatory regions.
2. For each cell, inspect unique nuclear fragments, TSS enrichment, FRiP,
   blacklist fraction, mitochondrial fraction, nucleosome signal, and doublet
   score jointly rather than applying one global cutoff.
3. Choose thresholds from each library's distributions, chemistry, tissue, and
   depth. Use published values only as starting diagnostics. Record each rule and
   pass/fail reason.
4. For multiome, also inspect RNA UMIs, detected genes, mitochondrial/ribosomal
   fractions, ambient RNA, and ATAC/RNA balance. Retain the original one-to-one
   barcode mapping and flag ATAC-low, RNA-low, and joint-low cells separately.
5. Detect ATAC doublets with SnapATAC2 and, when useful, AMULET. Combine this with
   Scrublet, genotype, hashing, or species-mixing evidence for paired data.
6. Recompute summaries after filtering and inspect results by donor and capture.

Read [references/qc-and-processing.md](references/qc-and-processing.md) for metric
definitions, starting values, and required reports.

## Build representations and targets

1. Use SnapATAC2 genome tiles for initial ATAC embedding. Check correlation with
   depth before interpreting clusters.
2. Create sample-aware cell-state pseudobulks. Call MACS3 peaks per supported
   pseudobulk, build a documented non-overlapping consensus, and recount all cells
   in the same regions.
3. Keep biological replicates separate through concordance checks. Preserve raw
   integer counts; store TF-IDF, log, CPM/RPM, and corrected values as derivatives.
4. Annotate with RNA markers, accessible marker loci, motif activity, reference
   mapping, and donor consistency. Keep hierarchical labels and confidence.
5. Export base-resolution ATAC as insertion profiles plus total counts, or export
   region-level replicate-aware counts with library-size metadata. Keep ATAC and
   RNA as distinct targets for multiome models.
6. For base-resolution ATAC, model Tn5 sequence bias and verify that the bias
   component does not absorb TF motifs. Mask blacklists, gaps, ambiguous sequence,
   and poor-mappability regions consistently.

Read [references/training-data.md](references/training-data.md) for concise target,
bias, background, and export guidance.

## Require these outputs

- pinned reference and annotation identifiers;
- raw and filtered fragment manifests with checksums;
- MuData/AnnData objects with raw counts and cell/sample QC metadata;
- consensus BED and excluded-region BED;
- pseudobulk count or insertion tracks with replicate metadata;
- target schema defining coordinates, units, transforms, offsets, and masks;
- before/after QC report with sample-level retention;
- software environments, commands, and a data sheet covering provenance,
  exclusions, licenses, and known biases.

Stop if assemblies or coordinate conventions disagree, paired barcodes cannot be
reconciled, sample provenance is missing, or reported counts cannot be traced to
source fragments.

Consult [references/sources.md](references/sources.md) before changing scientific
recommendations.
