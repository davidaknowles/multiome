# Primary sources and official guidance

Consult current versions before changing recommendations.

## Processing and QC

- [ENCODE ATAC-seq standards and processing pipeline](https://www.encodeproject.org/atac-seq/): bulk ATAC library standards, FRiP, TSS enrichment, replication, and uniform processing.
- [10x Cell Ranger ARC metric definitions](https://www.10xgenomics.com/support/software/cell-ranger-arc/latest/tutorials/outputs/metrics): current ATAC, GEX, and paired multiome metric definitions.
- [10x Cell Ranger ARC web summary](https://www.10xgenomics.com/support/software/cell-ranger-arc/latest/tutorials/outputs/web-summary): joint cell calling and library-level diagnostic interpretation.
- [SnapATAC2 standard pipeline](https://scverse.org/SnapATAC2/version/2.9/tutorials/pbmc.html) and [cell filtering API](https://scverse.org/SnapATAC2/version/2.9/api/_autosummary/snapatac2.pp.filter_cells.html): fragment/TSS QC and documented defaults.
- [Signac scATAC vignette](https://stuartlab.org/signac/1.11.0/articles/pbmc_vignette): joint visualization of fragment, TSS, FRiP, blacklist, and nucleosome metrics.
- [MACS3 callpeak documentation](https://macs3-project.github.io/MACS/docs/callpeak.html): paired-end BAMPE/BEDPE/FRAG peak calling and the distinction from single-end shift/extension.
- [ArchR](https://www.nature.com/articles/s41588-021-00790-6): scalable scATAC QC, doublet removal, clustering, peak construction, and multiome integration.
- [AMULET](https://pmc.ncbi.nlm.nih.gov/articles/PMC8408950/): read-count-based snATAC multiplet detection.
- [COMPOSITE multiome doublet framework](https://www.nature.com/articles/s41467-024-49448-x): evidence integration across paired modalities.

## Sequence-to-function modeling

- [ChromBPNet](https://pmc.ncbi.nlm.nih.gov/articles/PMC11741299/): bias-factorized base-resolution accessibility prediction and regulatory syntax.
- [ChromBPNet implementation](https://github.com/kundajelab/chrombpnet): input formats, preprocessing, bias modeling, and reports.
- [ChromBPNet bias-model guidance](https://github-wiki-see.page/m/kundajelab/chrombpnet/wiki/Bias-model-training): verify enzyme bias, avoid learning TF motifs, and match GC between background and peaks.
- [scBasset](https://www.nature.com/articles/s41592-022-01562-8): sequence-based modeling of single-cell ATAC accessibility.
- [Borzoi](https://www.nature.com/articles/s41588-024-02053-6): sequence-to-RNA coverage modeling relevant to a distinct RNA head in multiome models.
