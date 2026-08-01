# Sequence-to-function training-data reference

## Contents

1. Match targets to claims
2. Construct examples and negatives
3. Control assay and sequence bias
4. Split without leakage
5. Choose losses and evaluation
6. Export schema

## 1. Match targets to claims

| Claim | Preferred target | Avoid as sole target |
|---|---|---|
| Predict ATAC shape | insertion profile plus window count | peak presence only |
| Predict accessibility | replicate pseudobulk counts with depth offset | globally normalized binary calls |
| Predict cell state | masked multitask tracks across supported states | cell labels inferred from the same tested loci |
| Predict RNA output | gene/coverage counts as a separate head | gene-activity scores computed from ATAC |
| Predict variant effect | paired ref/alt predictions with allelic or perturbation labels | motif disruption alone as ground truth |

Aggregate sparse cells into biologically meaningful, replicate-preserving
pseudobulks for supervised sequence labels. Keep per-cell matrices for QC,
heterogeneity analysis, and uncertainty estimates; do not pretend a sparse binary
cell-by-peak observation is a noise-free functional label.

## 2. Construct examples and negatives

- Center profile examples on reproducible summits or fixed genomic anchors.
- Store input and output window coordinates separately; sequence context usually
  exceeds the scored target window.
- Retain counts, strand/cut convention, library size, replicate support, and masks.
- Sample negatives from callable, mappable sequence with GC and repeat properties
  comparable to positives. Separate closed regulatory candidates from arbitrary
  genomic background when the scientific question requires it.
- Exclude ambiguous bases, assembly gaps, unresolved blacklist regions, and
  low-mappability loci or explicitly model their masks.
- Keep all windows arising from one locus, peak, gene, ortholog group, or variant
  pair in one split group.

Do not train only on called peaks if the model must distinguish accessible from
inaccessible sequence. Conversely, do not let an excess of easy genomic negatives
dominate metrics.

## 3. Control assay and sequence bias

ATAC cut profiles contain Tn5 sequence preference, mapping bias, PCR/duplicate
effects, depth, and sample-quality variation. For base-resolution models:

- train or adopt a compatible Tn5 bias model from non-peak/background sequence;
- match bias-training background to peak GC and mappability;
- confirm the bias component learns the expected enzyme preference and not
  biological TF motifs;
- report performance for observed and bias-corrected components;
- retain strand/orientation conventions and apply reverse-complement augmentation
  consistently to sequence and profile labels.

Do not regress biological signal using covariates estimated from the test set.
Batch correction is for exploratory representations; prefer raw counts with
sample/task effects or explicit offsets for supervised targets.

## 4. Split without leakage

Create a split manifest before tuning. Use group-aware splits at both levels:

### Genomic groups

- chromosomes or large disjoint blocks for cis-regulatory sequence transfer;
- buffer neighboring blocks by at least the model's receptive field;
- group overlapping peaks/windows, genes with shared regulatory windows,
  structural haplotypes, ref/alt alleles, and orthologous loci.

### Biological groups

- donors/specimens for individual transfer;
- captures/libraries nested within donor;
- studies or laboratories for protocol transfer;
- cell types/tissues/species when that is the stated out-of-domain claim.

A strong evaluation contains: genomic holdout within known contexts, donor/study
holdout on known loci, and a joint holdout when feasible. Random cells leak donor,
library, and locus information. Random peaks leak nearby and overlapping sequence.

Within each fold, fit peak selection, task eligibility, normalization, negative
sampling, pseudobulk composition rules, feature selection, calibration, and early
stopping without test labels. Publish the exact split manifest.

## 5. Choose losses and evaluation

For cut profiles, jointly model profile shape and total counts using a count-aware
objective such as multinomial/profile likelihood plus Poisson or negative-binomial
count loss. For region counts, account for library size and overdispersion. Use
task masks rather than coding missing contexts as zero.

Report:

- profile correlation and Jensen-Shannon divergence or equivalent shape metric;
- count Pearson and Spearman correlation within each context;
- auPRC plus AUROC for imbalanced binary tasks;
- calibration and performance versus depth, GC, mappability, peak strength, and
  distance to TSS;
- results per donor, replicate, cell state, chromosome, and study;
- replicate-to-replicate agreement as an empirical ceiling;
- baseline comparisons: GC/mappability, mean track, k-mer/linear model, and a
  strong published architecture appropriate to the target;
- variant direction concordance and effect correlation on independent allelic or
  perturbation measurements.

Use bootstrap units matching the claim: loci for sequence transfer, donors for
biological transfer, or both with hierarchical bootstrap. Never calculate narrow
confidence intervals by treating correlated cells as independent replicates.

## 6. Export schema

Each example should resolve to fields equivalent to:

```text
example_id, assembly, chrom, input_start, input_end, target_start, target_end,
strand, locus_group, donor_group, study_group, cell_state, assay, replicate,
raw_count, library_size, target_uri, target_units, mask_uri, split, qc_version
```

Also export reference FASTA checksum, excluded-region checksum, task vocabulary,
coordinate convention, cut-site offset, transforms, pseudobulk membership,
licenses, and provenance from raw accession to target. Validate coordinate bounds,
split-group exclusivity, target shapes, finite values, and checksum stability.
