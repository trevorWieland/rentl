"""Storage adapters for persistence and artifacts."""

from rentl_io.storage.filesystem import (
    FileSystemArtifactStore,
    FileSystemLogStore,
    FileSystemRunStateStore,
)
from rentl_io.storage.log_sink import (
    CompositeLogSink,
    ConsoleLogSink,
    NoopLogSink,
    StorageLogSink,
    build_log_sink,
)
from rentl_io.storage.progress_sink import (
    CompositeProgressSink,
    FileSystemProgressSink,
    InMemoryProgressSink,
)

__all__ = [
    "CompositeLogSink",
    "CompositeProgressSink",
    "ConsoleLogSink",
    "FileSystemArtifactStore",
    "FileSystemLogStore",
    "FileSystemProgressSink",
    "FileSystemRunStateStore",
    "InMemoryProgressSink",
    "NoopLogSink",
    "StorageLogSink",
    "build_log_sink",
]
