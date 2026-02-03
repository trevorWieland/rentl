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
    ConsoleLogSink,
    FileSystemArtifactStore,
    FileSystemLogStore,
    FileSystemProgressSink,
    FileSystemRunStateStore,
    InMemoryProgressSink,
    NoopLogSink,
    StorageLogSink,
    build_log_sink,
)

__version__ = "0.1.0"

__all__ = [
    "CompositeLogSink",
    "CompositeProgressSink",
    "ConsoleLogSink",
    "CsvExportAdapter",
    "CsvIngestAdapter",
    "FileSystemArtifactStore",
    "FileSystemLogStore",
    "FileSystemProgressSink",
    "FileSystemRunStateStore",
    "InMemoryProgressSink",
    "JsonlExportAdapter",
    "JsonlIngestAdapter",
    "NoopLogSink",
    "StorageLogSink",
    "TxtExportAdapter",
    "TxtIngestAdapter",
    "build_log_sink",
    "get_export_adapter",
    "get_ingest_adapter",
    "load_source",
    "select_export_lines",
    "write_output",
    "write_phase_output",
]
