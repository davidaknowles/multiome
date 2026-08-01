"""Fetch public chromatin-accessibility dataset metadata."""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree

CELLXGENE_DATASETS = "https://api.cellxgene.cziscience.com/curation/v1/datasets"
CELLXGENE_COLLECTION = (
    "https://api.cellxgene.cziscience.com/curation/v1/collections/{collection_id}"
)
TENX_SITEMAP = "https://www.10xgenomics.com/sitemap-0.xml"
CATLAS_BROWSE_API = "https://www.catlas.org/catlas/dataset_browse.php"
CATLAS_RESOURCE = "https://www.catlas.org/catlas/dataset_resource.php?ID={dataset_id}"
ENCODE_MULTIOMICS_SEARCH = (
    "https://www.encodeproject.org/search/?type=MultiomicsSeries&status=released"
    "&limit=all&format=json"
)
MULTIOME_EFO = "EFO:0030059"
MAMMAL_SPECIES = {
    "Homo Sapiens",
    "Mus musculus",
    "Macaca mulatta",
    "Callithrix jacchus",
}
CATLAS_ATAC_TECHNOLOGIES = {"snATAC-seq", "sci-ATAC-seq", "10x multiome"}

# Calibrated against the 10x 10k PBMC Chromium X example: 107,754,854,400
# bytes FASTQ / 10,974 recovered nuclei. See data/storage_model.csv.
RAW_BYTES_PER_PRIMARY_CELL = 107_754_854_400 / 10_974


def fetch_bytes(url: str, timeout: int = 120, attempts: int = 3) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "multiome-catalog/0.1"})
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except Exception as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(1 + attempt)
    assert last_error is not None
    raise last_error


def fetch_json(url: str) -> Any:
    return json.loads(fetch_bytes(url))


def fetch_tsv(url: str) -> list[dict[str, str]]:
    """Fetch a small tab-separated repository report."""
    import csv
    import io

    return list(csv.DictReader(io.StringIO(fetch_bytes(url).decode("utf-8")), delimiter="\t"))


def remote_size(url: str, timeout: int = 120) -> int:
    """Return an HTTP asset's byte size without downloading its contents."""
    request = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": "multiome-catalog/0.1"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        length = response.headers.get("Content-Length")
    if length is None:
        raise RuntimeError(f"No Content-Length returned for {url}")
    return int(length)


def ena_fastq_files(
    accession: str,
    species: str = "",
    strategies: set[str] | None = None,
) -> list[dict[str, object]]:
    """Enumerate public FASTQs for an ENA study/project accession."""
    fields = "run_accession,scientific_name,library_strategy,fastq_ftp,fastq_bytes"
    query = urllib.parse.urlencode(
        {"accession": accession, "result": "read_run", "fields": fields, "format": "tsv"}
    )
    records = fetch_tsv(f"https://www.ebi.ac.uk/ena/portal/api/filereport?{query}")
    files: list[dict[str, object]] = []
    for record in records:
        if species and record["scientific_name"] != species:
            continue
        if strategies and record["library_strategy"] not in strategies:
            continue
        urls = record["fastq_ftp"].split(";") if record["fastq_ftp"] else []
        sizes = record["fastq_bytes"].split(";") if record["fastq_bytes"] else []
        if len(urls) != len(sizes):
            raise RuntimeError(f"ENA URL/size mismatch for {record['run_accession']}")
        for url, size in zip(urls, sizes):
            files.append(
                {
                    "run_accession": record["run_accession"],
                    "url": f"https://{url}",
                    "size_bytes": int(size),
                    "library_strategy": record["library_strategy"],
                }
            )
    return files


def fetch_json_post(url: str, payload: dict[str, str]) -> Any:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "multiome-catalog/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def labels(items: Iterable[dict[str, Any]]) -> str:
    return "; ".join(sorted({item["label"] for item in items}))


def cellxgene_multiome() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    datasets = [
        dataset
        for dataset in fetch_json(CELLXGENE_DATASETS)
        if any(
            assay.get("ontology_term_id") == MULTIOME_EFO
            for assay in dataset.get("assay", [])
        )
    ]
    collection_ids = sorted({dataset["collection_id"] for dataset in datasets})
    with ThreadPoolExecutor(max_workers=12) as pool:
        collections = list(
            pool.map(
                lambda collection_id: fetch_json(
                    CELLXGENE_COLLECTION.format(collection_id=collection_id)
                ),
                collection_ids,
            )
        )
    return datasets, {collection["collection_id"]: collection for collection in collections}


class _NextDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_next_data = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.in_next_data = tag == "script" and dict(attrs).get("id") == "__NEXT_DATA__"

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.in_next_data = False

    def handle_data(self, data: str) -> None:
        if self.in_next_data:
            self.parts.append(data)


def parse_tenx_page(html: bytes) -> dict[str, Any]:
    parser = _NextDataParser()
    parser.feed(html.decode("utf-8"))
    if not parser.parts:
        raise ValueError("10x page did not contain __NEXT_DATA__")
    return json.loads("".join(parser.parts))["props"]["pageProps"]


def tenx_dataset_urls() -> list[str]:
    root = ElementTree.fromstring(fetch_bytes(TENX_SITEMAP))
    return [
        element.text
        for element in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/")
        if element.text and "/datasets/" in element.text
    ]


def _fetch_tenx_page(url: str) -> tuple[str, dict[str, Any] | None]:
    try:
        page = parse_tenx_page(fetch_bytes(url))
    except Exception:
        return url, None
    dataset = page.get("dataset", {})
    product_name = dataset.get("product", {}).get("name", "")
    software_name = dataset.get("software", {}).get("name", "")
    if product_name != "Epi Multiome" and software_name != "Cell Ranger ARC":
        return url, None
    return url, page


def tenx_multiome() -> list[tuple[str, dict[str, Any]]]:
    with ThreadPoolExecutor(max_workers=24) as pool:
        pages = list(pool.map(_fetch_tenx_page, tenx_dataset_urls()))
    return [(url, page) for url, page in pages if page is not None]


def catlas_mammalian_scatac() -> list[dict[str, Any]]:
    """Return mammalian CATLAS records containing a chromatin-accessibility assay."""
    records = fetch_json_post(
        CATLAS_BROWSE_API,
        {
            "species": ";".join(sorted(MAMMAL_SPECIES)),
            "technology": ";".join(sorted(CATLAS_ATAC_TECHNOLOGIES)),
        },
    )
    if not isinstance(records, list):
        raise RuntimeError(f"Unexpected CATLAS response: {records!r}")
    return sorted(
        (
            record
            for record in records
            if record.get("Species") in MAMMAL_SPECIES
            and (
                "atac" in record.get("Sequencing", "").lower()
                or "multiome" in record.get("Sequencing", "").lower()
            )
        ),
        key=lambda record: record["DataID"],
    )


def encode_multiomics_series() -> list[dict[str, Any]]:
    """Return full metadata for every released ENCODE multiomics series."""
    search = fetch_json(ENCODE_MULTIOMICS_SEARCH)
    accessions = sorted(item["accession"] for item in search.get("@graph", []))
    with ThreadPoolExecutor(max_workers=24) as pool:
        records = list(
            pool.map(
                lambda accession: fetch_json(
                    f"https://www.encodeproject.org/experiments/{accession}/?format=json"
                ),
                accessions,
            )
        )
    return records


def encode_series_files(series: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten released assets from both component assays of an ENCODE series."""
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for dataset in series.get("related_datasets", []):
        for asset in dataset.get("files", []):
            accession = asset.get("accession", "")
            href = asset.get("href", "")
            if not accession or not href or accession in seen or asset.get("status") != "released":
                continue
            seen.add(accession)
            output_type = asset.get("output_type", "")
            is_raw = asset.get("file_format") == "fastq" and output_type in {
                "reads", "index reads"
            }
            result.append(
                {
                    "accession": accession,
                    "dataset_accession": dataset.get("accession", ""),
                    "assay": dataset.get("assay_term_name", ""),
                    "url": urllib.parse.urljoin("https://www.encodeproject.org", href),
                    "bytes": asset.get("file_size") or 0,
                    "title": output_type,
                    "filetype": classify_file(output_type, href),
                    "role": "raw" if is_raw else "processed",
                }
            )
    return result


def nested_numeric_values(value: Any, key: str) -> list[int]:
    """Collect integer-like values for a key from nested API metadata."""
    found: list[int] = []
    if isinstance(value, dict):
        for current_key, current_value in value.items():
            if current_key == key:
                try:
                    found.append(int(current_value))
                except (TypeError, ValueError):
                    pass
            found.extend(nested_numeric_values(current_value, key))
    elif isinstance(value, list):
        for item in value:
            found.extend(nested_numeric_values(item, key))
    return found


def geo_series_supplementary_urls(accession: str) -> list[str]:
    """Enumerate direct supplementary files exposed on a GEO series record."""
    query = urllib.parse.urlencode(
        {"targ": "self", "acc": accession, "form": "text", "view": "full"}
    )
    text = fetch_bytes(f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?{query}").decode(
        "utf-8"
    )
    urls = []
    for line in text.splitlines():
        if not line.startswith("!Series_supplementary_file = "):
            continue
        url = line.split(" = ", 1)[1].strip()
        if url.lower() != "none":
            urls.append(url.replace("ftp://", "https://", 1))
    return list(dict.fromkeys(urls))


def extract_doi(article: str) -> str:
    """Extract and lightly normalize a DOI from CATLAS publication text."""
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", article, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(0).rstrip(".,;)")


def classify_file(title: str, url: str) -> str:
    text = f"{title} {url}".lower()
    if "fastq" in text or "sequencing data" in text:
        return "FASTQ"
    if "fragment" in text and not text.endswith(".tbi"):
        return "fragment"
    if "bigwig" in text or url.lower().endswith((".bw", ".bigwig")):
        return "bigwig"
    if re.search(r"\.bed(?:\.gz)?(?:\?|$)", url.lower()) or "peak locations" in text:
        return "BED"
    if "h5ad" in text:
        return "H5AD"
    if "loom" in text:
        return "LOOM"
    if "matrix market" in text or ".mtx" in text:
        return "MTX"
    if ".rds" in text:
        return "RDS"
    if ".snap" in text:
        return "SNAP"
    suffix = Path(url.split("?", 1)[0]).suffix.lower().lstrip(".")
    return suffix.upper() if suffix else title


def tenx_files(page: dict[str, Any]) -> list[dict[str, Any]]:
    fileset_map = page.get("filesetMap", {})
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in fileset_map.values():
        if not isinstance(group, dict):
            continue
        for kind in ("inputs", "outputs", "summaries"):
            for asset in group.get(kind, []):
                url = asset.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                result.append({**asset, "role": "raw" if kind == "inputs" else "processed"})
    return result
