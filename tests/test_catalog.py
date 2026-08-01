import unittest

from multiome_catalog.catalog import classify_file, extract_doi


class FileClassificationTest(unittest.TestCase):
    def test_requested_formats(self):
        self.assertEqual(classify_file("ATAC peak locations", "https://example/a.bed"), "BED")
        self.assertEqual(classify_file("ATAC smoothed track", "https://example/a.bigwig"), "bigwig")
        self.assertEqual(classify_file("ATAC Per fragment information", "https://example/a.tsv.gz"), "fragment")
        self.assertEqual(classify_file("Sequencing data (FASTQ)", "https://example/fastqs.tar"), "FASTQ")
        self.assertEqual(classify_file("peak matrix", "https://example/peaks.loom.gz"), "LOOM")
        self.assertEqual(classify_file("matrix", "https://example/matrix.mtx.gz"), "MTX")
        self.assertEqual(classify_file("object", "https://example/object.RDS.gz"), "RDS")


class DoiExtractionTest(unittest.TestCase):
    def test_catlas_article_doi(self):
        self.assertEqual(
            extract_doi("Nature (2024). https://doi.org/10.1038/s41586-024-07234-1"),
            "10.1038/s41586-024-07234-1",
        )

    def test_trailing_publication_punctuation(self):
        self.assertEqual(
            extract_doi("Cell 174 (2018), doi: 10.1016/j.cell.2018.06.052."),
            "10.1016/j.cell.2018.06.052",
        )
