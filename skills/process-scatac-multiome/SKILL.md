---
name: process-scatac-multiome
description: Design, implement, review, or troubleshoot reproducible scATAC-seq, snATAC-seq, and paired RNA+ATAC multiome processing workflows, including raw-read processing, sample- and cell-level QC, doublet removal, peak and count construction, cell-state annotation, pseudobulk aggregation, and preparation of leakage-resistant targets for DNA sequence-to-function models. Use for FASTQ, BAM/CRAM, fragments.tsv.gz, peak BED, sparse matrix, H5/H5AD, or multiome analysis tasks intended for regulatory sequence prediction, accessibility modeling, variant-effect prediction, or model benchmarking.
---

# Process scATAC and Multiome

Build analysis-ready and model-ready data without hiding assay failures, donor
structure, technical bias, or label leakage. Prefer a reproducible workflow with
immutable intermediate artifacts over one-off notebook processing.

## Start with a data contract

Record before processing:

- biological unit: donor, specimen, region, condition, time point, cell state;
- assay and chemistry, paired versus unpaired modalities, and read structure;
- reference assembly, primary contigs, gene annotation, blacklist, and decoys;
- raw accessions, checksums, pipeline/container versions, parameters, and seeds;
- intended prediction unit: cut profile, fixed bin, peak, enhancer, gene, or variant;
- intended generalization axis: unseen loci, donors, cell types, tissues, studies,
  species, or combinations of these.

Do not merge samples or select cells until donor and library identifiers are
recoverable from every fragment and matrix column.

## Choose the processing entry point

- From FASTQ: use the chemistry-aware vendor pipeline when applicable, or a
  documented barcode-aware equivalent. Align each library independently.
- From BAM/CRAM: verify assembly, contig naming, barcode tags, paired-read status,
  duplicate policy, MAPQ policy, and Tn5 cut-site convention.
- From fragments: verify coordinate semantics, sorting, tabix index, multiplicity
  column, barcode namespace, assembly, and whether duplicates were collapsed.
- From matrices/H5AD only: treat fragment-derived QC and base-resolution training
  targets as unavailable unless the original fragments can be recovered.

Preserve raw fragments. Derive filtered fragments, matrices, peaks, and tracks as
separate versioned products.

## Process reads and fragments

1. Inspect read quality, index balance, barcode validity, adapter/read-through,
   and per-library depth before pooling.
2. Align to one pinned reference. Retain high-quality, properly paired nuclear
   fragments; report mitochondrial, non-primary, chimeric, duplicate, and low-MAPQ
   fractions rather than silently discarding them.
3. Apply the pipeline's documented Tn5 insertion offset exactly once. Store both
   fragment intervals and insertion sites when base-resolution targets are needed.
4. Remove or mask assembly gaps, blacklist regions, anomalous contigs, and regions
   with poor mappability as appropriate to the model task. Never mask test loci
   using labels learned from the complete dataset.
5. Generate library-level fragment length, TSS aggregate, barcode-rank, mapping,
   duplication, and signal-in-feature reports.

For detailed metrics and threshold selection, read
[references/qc-and-processing.md](references/qc-and-processing.md).

## Perform QC in layers

Apply QC separately per library before integration.

1. Gate failed libraries using mapping, barcode, complexity, fragment periodicity,
   TSS enrichment, and fraction-in-peaks or fraction-in-regulatory-regions.
2. Identify cell-containing barcodes using rank/mixture evidence. Do not equate a
   single fragment cutoff with cell calling.
3. Jointly inspect log fragments, TSS enrichment, FRiP, blacklist fraction,
   mitochondrial fraction, nucleosome signal, and library membership.
4. For multiome, additionally inspect RNA UMIs, detected genes, mitochondrial and
   ribosomal fractions, ATAC/RNA balance, and whether either modality supports the
   cell call. Flag modality-specific failures instead of automatically discarding
   biologically plausible cells.
5. Detect multiplets within each capture using at least one ATAC-aware method; for
   paired multiome, combine evidence from both modalities and sample/genotype
   demultiplexing when available.
6. Recompute summaries after filtering and inspect clusters for low-quality,
   doublet, ambient-RNA, and donor-specific structure.

Treat published cutoffs as starting diagnostics. Choose thresholds from each
library's distributions, chemistry, tissue, depth, and downstream resolution.
Record every rule and the number of cells removed by sample and annotated class.
Never optimize QC cutoffs against final test-set performance.

## Construct biological representations

- Build a genome-wide tile or k-mer representation for initial dimensionality
  reduction so discovery is not restricted to peaks called on all cells.
- Call peaks on pseudobulks grouped by sample and sufficiently supported cell
  state. Retain biological replicates; do not pool donors into one unreplicated
  track before measuring concordance.
- Form a reproducible non-overlapping consensus peak set using fixed width around
  summits or a documented interval-reduction rule. Quantify every cell/sample in
  that same feature space.
- Use TF-IDF/LSI or an appropriate count model for ATAC embeddings; diagnose depth
  correlation. Integrate batches only after preserving donor and condition axes.
- Annotate cell states using RNA markers, accessibility at marker loci, motif
  activity, reference mapping, and donor consistency. Keep labels hierarchical
  and attach confidence rather than forcing unsupported fine labels.
- Use matched RNA from the same barcode as paired evidence, not as proof that a
  nearby accessible peak regulates a gene. Validate peak-gene links across donors
  or perturbations where possible.

Use MACS3 paired-end/fragment modes for paired fragments unless a chosen workflow
has a justified alternative. Do not apply single-end shift/extension recipes to
paired-end fragments.

## Build sequence-to-function targets

Select targets that retain the measurement model:

- base-resolution ATAC: strand-aware or unstranded insertion counts plus total
  counts per window;
- region accessibility: replicate-aware pseudobulk counts with library-size
  offsets, not only thresholded peak labels;
- cell-state multitask: one target per supported cell state/sample, with a mask for
  missing or underpowered tasks;
- multiome: accessibility profiles and RNA expression/coverage as distinct heads,
  preserving pairing and measurement-specific normalization;
- variant effects: reference/alternate sequence pairs evaluated in the same
  context, with allele-aware experimental labels where available.

Train a Tn5 sequence-bias component for base-resolution accessibility models and
verify that it learns enzyme bias rather than TF motifs. Match GC and mappability
between peaks and background. Keep raw counts and depth metadata even when also
exporting normalized tracks.

Read [references/training-data.md](references/training-data.md) before defining
examples, negatives, splits, losses, or evaluation metrics.

## Prevent leakage

Define splits before final feature selection and target construction.

- Hold out chromosomes or disjoint genomic blocks for locus generalization.
- Hold out donors, specimens, or studies for biological generalization.
- Use both axes when claiming transfer to unseen sequence and unseen biology.
- Keep overlapping windows, alternative peak widths, orthologous loci, and variant
  alleles in the same split group.
- Fit peak selection, normalization, annotations used as labels, background
  sampling, and hyperparameters using training data only.
- Never place cells from one donor/library in both train and test merely because
  they are different barcodes.
- Freeze the test set and report validation-driven decisions.

Random window or random cell splits are not adequate evidence of generalization.

## Require model-ready outputs

Produce:

- pinned reference FASTA and annotation identifiers;
- raw and QC-filtered fragment manifests with checksums;
- cell metadata with donor/library/capture, QC metrics, labels, confidence, and
  explicit pass/fail reasons;
- consensus regions and excluded-region BED files;
- raw count matrices and pseudobulk cut/count tracks with replicate metadata;
- split manifest assigning every locus and biological unit to one split;
- target schema defining coordinates, transforms, offsets, masks, and units;
- QC report before/after filtering and model-data datasheet documenting known
  biases, exclusions, licenses, and permitted uses.

Fail the workflow if assemblies or coordinate conventions disagree, paired
barcodes cannot be reconciled, split groups overlap, direct target provenance is
missing, or a claimed held-out axis is present in training.

## Consult supporting references

- Read [references/qc-and-processing.md](references/qc-and-processing.md) for QC
  definitions, practical starting values, peak construction, and multiome checks.
- Read [references/training-data.md](references/training-data.md) for target,
  negative, split, bias, loss, and evaluation design.
- Read [references/sources.md](references/sources.md) when reporting or revising
  recommendations; prefer the linked official documentation and primary papers.
