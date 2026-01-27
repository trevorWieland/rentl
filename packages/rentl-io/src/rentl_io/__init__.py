"""rentl-io: Input/Output adapters."""

from rentl_io.export import (
    CsvExportAdapter,
    JsonlExportAdapter,
    TxtExportAdapter,
    get_export_adapter,
    select_export_lines,
    write_output,
    write_phase_output,
)
from rentl_io.ingest import (
    CsvIngestAdapter,
    JsonlIngestAdapter,
    TxtIngestAdapter,
    get_ingest_adapter,
    load_source,
)
from rentl_io.storage import (
    CompositeLogSink,
    CompositeProgressSink,
    FileSystemArtifactStore,
    FileSystemLogStore,
    FileSystemProgressSink,
    FileSystemRunStateStore,
    InMemoryProgressSink,
    StorageLogSink,
)

__version__ = "0.1.0"

__all__ = [
    "CompositeLogSink",
    "CompositeProgressSink",
    "CsvExportAdapter",
    "CsvIngestAdapter",
    "FileSystemArtifactStore",
    "FileSystemLogStore",
    "FileSystemProgressSink",
    "FileSystemRunStateStore",
    "InMemoryProgressSink",
    "JsonlExportAdapter",
    "JsonlIngestAdapter",
    "StorageLogSink",
    "TxtExportAdapter",
    "TxtIngestAdapter",
    "get_export_adapter",
    "get_ingest_adapter",
    "load_source",
    "select_export_lines",
    "write_output",
    "write_phase_output",
]
