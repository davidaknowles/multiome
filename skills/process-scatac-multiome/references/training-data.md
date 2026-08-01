# Sequence-to-function targets

## Choose measurements, not proxies

| Goal | Preferred target |
|---|---|
| ATAC shape | insertion profile plus total count per window |
| Accessibility | replicate-aware pseudobulk counts with depth metadata |
| Cell-state activity | one masked target per supported state/sample |
| Multiome output | separate accessibility and RNA count/coverage targets |
| Variant effects | paired reference/alternate sequences with allelic or perturbation measurements |

Aggregate sparse cells into biologically meaningful, replicate-preserving
pseudobulks. Retain per-cell matrices for QC and uncertainty. Do not use sparse
cell-by-peak binaries or ATAC gene-activity scores as noise-free functional labels.

## Prepare regions and background

- Center profile targets on reproducible summits or fixed anchors.
- Store input-sequence and scored-output coordinates separately.
- Retain raw counts, library size, replicate support, cut convention, and masks.
- Sample background from callable sequence with GC, repeat, and mappability
  properties comparable to foreground regions.
- Mask ambiguous bases, assembly gaps, blacklists, and poor-mappability regions.
- Keep reference and alternate allele targets in the same coordinate convention.

Use pysam/pyfaidx for sequence, bioframe/PyRanges for intervals, pyBigWig for
tracks, scipy sparse/AnnData for matrices, and PyArrow/Parquet or Zarr for large
tables and arrays.

## Control assay bias

ATAC profiles contain Tn5 preference, mapping bias, duplicates, depth, and sample
quality effects. Follow ChromBPNet conventions for base-resolution targets:

- build insertion profiles with a documented Tn5 offset;
- use compatible non-peak/background sequence for a Tn5 bias component;
- match background GC and mappability to peaks;
- verify that the bias component learns enzyme preference rather than TF motifs;
- retain strand/orientation conventions and transform sequence and profiles
  together under reverse complementation;
- preserve raw counts and depth covariates even when exporting normalized tracks.

Use corrected embeddings only for exploration. Do not replace supervised count
targets with batch-corrected values.

## Export a stable schema

Each example should resolve to fields equivalent to:

```text
example_id, assembly, chrom, input_start, input_end, target_start, target_end,
strand, locus_group, donor, sample, cell_state, assay, replicate, raw_count,
library_size, target_uri, target_units, mask_uri, qc_version
```

Also export FASTA and exclusion-mask checksums, task vocabulary, coordinate and
cut-site conventions, transforms, pseudobulk membership, licenses, and provenance.
Validate coordinate bounds, shapes, finite values, and checksum stability.
