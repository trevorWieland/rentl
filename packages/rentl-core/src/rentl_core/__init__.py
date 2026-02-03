"""rentl-core: Core pipeline logic for rentl."""

from rentl_core.orchestrator import (
    PhaseAgentPool,
    PipelineOrchestrator,
    PipelineRunContext,
    hydrate_run_context,
)
from rentl_core.ports import (
    ExportAdapterProtocol,
    ExportBatchError,
    ExportError,
    ExportErrorCode,
    ExportErrorDetails,
    ExportErrorInfo,
    ExportEvent,
    ExportResult,
    ExportSummary,
    IngestAdapterProtocol,
    IngestBatchError,
    IngestError,
    IngestErrorCode,
    IngestErrorDetails,
    IngestErrorInfo,
    IngestEvent,
    build_export_completed_log,
    build_export_failed_log,
    build_export_started_log,
    build_ingest_completed_log,
    build_ingest_failed_log,
    build_ingest_started_log,
)
from rentl_core.status import build_status_result
from rentl_core.telemetry import AgentTelemetryEmitter
from rentl_core.version import VERSION

__version__ = "0.1.0"

__all__ = [
    "VERSION",
    "AgentTelemetryEmitter",
    "ExportAdapterProtocol",
    "ExportBatchError",
    "ExportError",
    "ExportErrorCode",
    "ExportErrorDetails",
    "ExportErrorInfo",
    "ExportEvent",
    "ExportResult",
    "ExportSummary",
    "IngestAdapterProtocol",
    "IngestBatchError",
    "IngestError",
    "IngestErrorCode",
    "IngestErrorDetails",
    "IngestErrorInfo",
    "IngestEvent",
    "PhaseAgentPool",
    "PipelineOrchestrator",
    "PipelineRunContext",
    "build_export_completed_log",
    "build_export_failed_log",
    "build_export_started_log",
    "build_ingest_completed_log",
    "build_ingest_failed_log",
    "build_ingest_started_log",
    "build_status_result",
    "hydrate_run_context",
]
