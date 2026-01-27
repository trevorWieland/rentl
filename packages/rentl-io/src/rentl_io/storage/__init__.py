"""Storage adapters for persistence and artifacts."""

from rentl_io.storage.filesystem import (
    FileSystemArtifactStore,
    FileSystemLogStore,
    FileSystemRunStateStore,
)
from rentl_io.storage.log_sink import CompositeLogSink, StorageLogSink
from rentl_io.storage.progress_sink import (
    CompositeProgressSink,
    FileSystemProgressSink,
    InMemoryProgressSink,
)

__all__ = [
    "CompositeLogSink",
    "CompositeProgressSink",
    "FileSystemArtifactStore",
    "FileSystemLogStore",
    "FileSystemProgressSink",
    "FileSystemRunStateStore",
    "InMemoryProgressSink",
    "StorageLogSink",
]
