"""Import adapters for ingesting source lines."""

from rentl_io.ingest.csv_adapter import CsvIngestAdapter
from rentl_io.ingest.jsonl_adapter import JsonlIngestAdapter
from rentl_io.ingest.router import get_ingest_adapter, load_source
from rentl_io.ingest.txt_adapter import TxtIngestAdapter

__all__ = [
    "CsvIngestAdapter",
    "JsonlIngestAdapter",
    "TxtIngestAdapter",
    "get_ingest_adapter",
    "load_source",
]
