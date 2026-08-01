import unittest

from multiome_catalog.catalog import classify_file


class FileClassificationTest(unittest.TestCase):
    def test_requested_formats(self):
        self.assertEqual(classify_file("ATAC peak locations", "https://example/a.bed"), "BED")
        self.assertEqual(classify_file("ATAC smoothed track", "https://example/a.bigwig"), "bigwig")
        self.assertEqual(classify_file("ATAC Per fragment information", "https://example/a.tsv.gz"), "fragment")
        self.assertEqual(classify_file("Sequencing data (FASTQ)", "https://example/fastqs.tar"), "FASTQ")
