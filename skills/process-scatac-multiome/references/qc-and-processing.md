# QC and processing reference

## Contents

1. Principles
2. Library-level QC
3. Cell-level ATAC QC
4. Multiome RNA and pairing QC
5. Multiplets and contamination
6. Peak and matrix construction
7. Required reports

## 1. Principles

Use thresholds to distinguish technical failure, not to maximize apparent cluster
separation. Compute metrics per capture with a single pinned annotation. TSS
enrichment implementations differ, so do not compare numerical values across
pipelines without checking definitions. Avoid hard removal based on one metric;
inspect joint distributions and retain pass/fail reasons.

Thresholds below are starting points for visualization or mixture fitting, not
universal acceptance criteria. Small cells, frozen tissue, tumor, developmental,
and non-model-organism samples can have shifted distributions.

## 2. Library-level QC

Report for each FASTQ/library:

| Area | Metrics and checks |
|---|---|
| Sequencing | read pairs, Q30 by read/index, barcode validity, saturation |
| Mapping | MAPQ-filtered proper pairs, unmapped, chimeric, mitochondrial/non-nuclear |
| Complexity | duplicate fraction, unique nuclear fragments, complexity curve |
| ATAC signal | TSS enrichment/profile, FRiP, blacklist fraction, fragment periodicity |
| Cell recovery | barcode-rank curve, called cells, fragments in called cells |
| Replication | depth-normalized peak/profile correlation between biological replicates |

ENCODE bulk ATAC guidance treats FRiP above 0.3 as good and above 0.2 as
acceptable, but bulk values are not cell-level gates. For 10x assays, compare
library metrics with chemistry-specific vendor expectations and inspect alerts.

Reject or quarantine a library when multiple independent signals indicate failure:
poor mapping/barcodes, absent TSS enrichment, no nucleosomal periodicity, low
complexity, dominant background, or poor concordance unsupported by biology.

## 3. Cell-level ATAC QC

Compute at minimum:

- unique nuclear fragments;
- TSS enrichment using the selected pipeline's definition;
- fraction of fragments or insertion events in consensus peaks;
- blacklist fraction and mitochondrial/non-primary fraction;
- nucleosome signal or nucleosome-free/mono-nucleosomal balance;
- duplicate burden when recoverable;
- doublet score and capture/library identity.

Useful initial views are log10 fragments versus TSS enrichment, fragments versus
FRiP, and each metric stratified by library. SnapATAC2 defaults of 1,000 fragments
and TSS enrichment 5 are reasonable plot anchors, not universal gates. A common
high-complexity analysis may start exploring 1,000–5,000 fragments, TSS enrichment
4–10, and FRiP 0.15–0.30, then select sample-aware boundaries from the observed
good-cell mode. Do not transplant these ranges across TSS implementations.

Check both lower and upper tails: unusually high fragments/features often indicate
multiplets. Low mitochondrial fraction is generally desirable, but a universal
percentage cutoff is inappropriate across tissues and nuclei preparations.

When peak definitions are unavailable, use TSS and tile/regulatory-region signal
for initial QC. Recompute FRiP after a consensus peak set exists, but do not let
test samples define training peaks in a predictive benchmark.

## 4. Multiome RNA and pairing QC

Retain the one-to-one ATAC/RNA barcode mapping. Report RNA UMIs, detected genes,
mitochondrial and ribosomal fractions, ambient-RNA evidence, and ATAC/RNA depth
alongside ATAC metrics.

Classify cells into joint-good, ATAC-low, RNA-low, and joint-low states. Review
modality-low states by cell type and sample before removal; genuine biology can
produce low transcription or accessibility. Inspect correlations between ATAC
gene activity and RNA expression only as QC/annotation support, not as a direct
regulatory ground truth.

Do not independently filter ATAC and RNA matrices and silently intersect them.
Start from the joint cell calls, apply documented modality-aware rules, and retain
the disposition of every original barcode.

## 5. Multiplets and contamination

Run multiplet detection within each capture. Use ATAC-aware simulated-neighbor
methods and/or read-count methods such as AMULET. For multiome, combine ATAC and
RNA doublet evidence; add genotype, hashing, or species-mixing evidence when
available. Calibrate expected rates from loading rather than applying one rate to
all captures.

Flag clusters with incompatible lineage markers, excessive depth, discordant
modalities, or donor mixing even if an algorithmic score is below threshold.
Estimate ambient RNA and avoid using ambient marker expression to label ATAC cell
states.

## 6. Peak and matrix construction

1. Cluster initially with genome tiles or another peak-independent representation.
2. Create pseudobulks per sample and broad cell state. Require minimum cells and
   fragments; merge rare states only when biologically defensible.
3. Call peaks per pseudobulk with paired-fragment-aware settings. Preserve summit,
   score, sample, and cell-state provenance.
4. Construct a fixed-width, non-overlapping consensus. Exclude blacklists and poor
   mappability. Quantify all cells and replicates in the frozen set.
5. Keep raw integer counts. Store any TF-IDF, CPM/RPM, log, quantile, or batch-
   corrected representation as a derivative with parameters.
6. Measure replicate concordance and state specificity before pooling.

For sequence modeling, do not use a union called from train and test samples.
Either define loci from external annotations without test labels or construct the
training candidate set inside each split. Evaluation may use a separately frozen,
predeclared locus set.

## 7. Required reports

Produce per-library and aggregate reports containing:

- metric distributions before and after each gate;
- pass/fail counts by donor, tissue, condition, cell state, and capture;
- threshold rationale and sensitivity analysis near each boundary;
- doublet calls and cross-modality discordance;
- replicate concordance and depth/quality confounding of embeddings;
- files, checksums, software versions, annotations, and commands;
- exclusions and any sample or class made underpowered by QC.
