#!/usr/bin/env bash
#
# orchestrate.sh — Automated spec implementation loop
#
# Sequences: do-task → task gate → audit-task → (repeat) → spec gate → run-demo → audit-spec
# The intelligence lives in the agents. This script only does sequencing, gating, and routing.
#
# Usage:
#   ./orchestrate.sh <spec-folder>
#   ./orchestrate.sh <spec-folder> --config orchestrate.conf
#
# The spec folder must contain spec.md and plan.md (output of shape-spec).
#
# Configuration (via env vars, config file, or CLI flags):
#   ORCH_CLI           - CLI command for headless agent invocation (default: "claude -p")
#   ORCH_DO_MODEL      - Model for do-task (default: unset, uses CLI default)
#   ORCH_AUDIT_MODEL   - Model for audit-task (default: unset, uses CLI default)
#   ORCH_DEMO_MODEL    - Model for run-demo (default: unset, uses CLI default)
#   ORCH_SPEC_MODEL    - Model for audit-spec (default: unset, uses CLI default)
#   ORCH_TASK_GATE     - Task-level verification command (default: "make check")
#   ORCH_SPEC_GATE     - Spec-level verification command (default: "make all")
#   ORCH_MAX_CYCLES    - Safety limit on full cycles (default: 10, staleness detector is primary)
#   ORCH_COMMANDS_DIR  - Path to command markdown files (default: ".claude/commands/agent-os")

set -euo pipefail

# --- Colors and output helpers ---

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

log()    { echo -e "${BLUE}[orch]${NC} $*"; }
ok()     { echo -e "${GREEN}[orch]${NC} $*"; }
warn()   { echo -e "${YELLOW}[orch]${NC} $*"; }
fail()   { echo -e "${RED}[orch]${NC} $*"; }
header() { echo -e "\n${BOLD}═══ $* ═══${NC}\n"; }

# Play the victory fanfare (best-effort, never blocks on failure)
fanfare() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local wav="$script_dir/fanfare.wav"
    if [[ ! -f "$wav" ]]; then return; fi

    # Try playback methods in order of preference (background, fire-and-forget)
    if command -v paplay &>/dev/null; then
        paplay "$wav" &>/dev/null &
    elif command -v aplay &>/dev/null; then
        aplay -q "$wav" &>/dev/null &
    elif command -v mpv &>/dev/null; then
        mpv --no-video --really-quiet "$wav" &>/dev/null &
    elif command -v ffplay &>/dev/null; then
        ffplay -nodisp -autoexit -loglevel quiet "$wav" &>/dev/null &
    elif command -v powershell.exe &>/dev/null; then
        local win_path
        win_path=$(wslpath -w "$wav" 2>/dev/null) || return
        powershell.exe -c "(New-Object Media.SoundPlayer '$win_path').PlaySync()" &>/dev/null &
    fi
}

# --- Configuration ---

SPEC_FOLDER="${1:?Usage: orchestrate.sh <spec-folder>}"
shift

# Defaults
CLI="${ORCH_CLI:-claude -p}"
DO_MODEL="${ORCH_DO_MODEL:-}"
AUDIT_MODEL="${ORCH_AUDIT_MODEL:-}"
DEMO_MODEL="${ORCH_DEMO_MODEL:-}"
SPEC_MODEL="${ORCH_SPEC_MODEL:-}"
TASK_GATE="${ORCH_TASK_GATE:-make check}"
SPEC_GATE="${ORCH_SPEC_GATE:-make all}"
MAX_CYCLES="${ORCH_MAX_CYCLES:-10}"
COMMANDS_DIR="${ORCH_COMMANDS_DIR:-.claude/commands/agent-os}"

# Load config file if provided
while [[ $# -gt 0 ]]; do
    case "$1" in
        --config)
            if [[ -f "$2" ]]; then
                # shellcheck source=/dev/null
                source "$2"
            else
                fail "Config file not found: $2"
                exit 1
            fi
            shift 2
            ;;
        *)
            fail "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Validate spec folder
if [[ ! -f "$SPEC_FOLDER/spec.md" ]]; then
    fail "spec.md not found in $SPEC_FOLDER"
    exit 1
fi
if [[ ! -f "$SPEC_FOLDER/plan.md" ]]; then
    fail "plan.md not found in $SPEC_FOLDER"
    exit 1
fi

# --- Helper functions ---

# Build CLI command with optional model flag
build_cmd() {
    local model="$1"
    local cmd="$CLI"
    if [[ -n "$model" ]]; then
        cmd="$cmd --model $model"
    fi
    echo "$cmd"
}

# Invoke an agent command by reading its markdown file and passing it as a prompt
invoke_agent() {
    local command_name="$1"
    local model="$2"
    local extra_context="${3:-}"

    local command_file="$COMMANDS_DIR/${command_name}.md"
    if [[ ! -f "$command_file" ]]; then
        fail "Command file not found: $command_file"
        return 1
    fi

    local prompt
    prompt="$(cat "$command_file")"
    prompt="$prompt

---

Spec folder: $SPEC_FOLDER

$extra_context"

    local cmd
    cmd=$(build_cmd "$model")

    log "Invoking $command_name..."
    local output
    output=$(eval "$cmd" <<< "$prompt" 2>&1) || true
    echo "$output"
}

# Extract exit signal from agent output
extract_signal() {
    local output="$1"
    local prefix="$2"
    echo "$output" | grep -oP "${prefix}: \K\w[\w-]*" | tail -1
}

# Count unchecked tasks in plan.md
count_unchecked() {
    grep -cP '^\s*- \[ \]' "$SPEC_FOLDER/plan.md" 2>/dev/null || echo "0"
}

# Get a snapshot of plan.md for staleness detection
plan_snapshot() {
    md5sum "$SPEC_FOLDER/plan.md" 2>/dev/null | cut -d' ' -f1
}

# Check audit.md status field
audit_status() {
    head -1 "$SPEC_FOLDER/audit.md" 2>/dev/null | grep -oP 'status: \K\w+' || echo "unknown"
}

# --- Main loop ---

header "Orchestrator Starting"
log "Spec folder: $SPEC_FOLDER"
log "Task gate: $TASK_GATE"
log "Spec gate: $SPEC_GATE"
log "CLI: $CLI"
echo ""

cycle=0
prev_snapshot=""

while true; do
    cycle=$((cycle + 1))

    if [[ $cycle -gt $MAX_CYCLES ]]; then
        fail "Safety limit reached ($MAX_CYCLES cycles). Stopping."
        fail "Check signposts.md and audit-log.md for context on what's stuck."
        exit 1
    fi

    header "Cycle $cycle"

    # Staleness detection: compare plan.md to previous cycle
    current_snapshot=$(plan_snapshot)
    if [[ -n "$prev_snapshot" && "$current_snapshot" == "$prev_snapshot" ]]; then
        fail "Staleness detected — plan.md unchanged since last cycle."
        fail "The loop is spinning without making progress."
        fail ""
        fail "Context for human review:"
        if [[ -f "$SPEC_FOLDER/signposts.md" ]]; then
            fail "  Signposts: $SPEC_FOLDER/signposts.md"
        fi
        if [[ -f "$SPEC_FOLDER/audit-log.md" ]]; then
            fail "  Audit log: $SPEC_FOLDER/audit-log.md"
        fi
        exit 1
    fi
    prev_snapshot="$current_snapshot"

    # ─── Phase 1: Task Loop ───

    while true; do
        unchecked=$(count_unchecked)
        if [[ "$unchecked" -eq 0 ]]; then
            ok "All tasks checked off."
            break
        fi

        log "$unchecked unchecked task(s) remaining."

        # --- do-task ---
        header "Phase 1: do-task"
        output=$(invoke_agent "do-task" "$DO_MODEL")
        signal=$(extract_signal "$output" "do-task-status")

        case "$signal" in
            complete)
                ok "do-task: task completed."
                ;;
            all-done)
                ok "do-task: all tasks done."
                break
                ;;
            blocked)
                warn "do-task: blocked. Check signposts.md."
                fail "Human intervention needed."
                exit 1
                ;;
            error)
                fail "do-task: error. Output:"
                echo "$output" | tail -20
                exit 1
                ;;
            *)
                warn "do-task: unrecognized signal '$signal'. Continuing cautiously."
                ;;
        esac

        # --- Task gate (orchestrator runs verification) ---
        log "Running task gate: $TASK_GATE"
        if ! eval "$TASK_GATE" 2>&1; then
            warn "Task gate failed. Re-invoking do-task with error context."
            gate_output=$(eval "$TASK_GATE" 2>&1 || true)
            output=$(invoke_agent "do-task" "$DO_MODEL" \
                "The orchestrator's task gate ($TASK_GATE) failed after your last task. Fix the issue and ensure the gate passes before completing the task.

Error output:
$gate_output")
            signal=$(extract_signal "$output" "do-task-status")

            if [[ "$signal" == "blocked" ]]; then
                fail "do-task: still blocked after gate failure. Human intervention needed."
                exit 1
            fi

            # Re-run gate
            if ! eval "$TASK_GATE" 2>&1; then
                fail "Task gate still failing after do-task retry. Stopping."
                exit 1
            fi
        fi
        ok "Task gate passed."

        # --- audit-task ---
        header "Phase 1: audit-task"
        output=$(invoke_agent "audit-task" "$AUDIT_MODEL")
        signal=$(extract_signal "$output" "audit-task-status")

        case "$signal" in
            pass)
                ok "audit-task: task passed audit."
                ;;
            fail)
                warn "audit-task: issues found. Fix items added to plan.md."
                # Loop continues — do-task will pick up the fix items
                ;;
            error)
                fail "audit-task: error. Output:"
                echo "$output" | tail -20
                exit 1
                ;;
            *)
                warn "audit-task: unrecognized signal '$signal'. Continuing cautiously."
                ;;
        esac
    done

    # ─── Phase 2: Spec Gate ───

    header "Phase 2: Spec Gate"
    log "Running spec gate: $SPEC_GATE"
    if ! eval "$SPEC_GATE" 2>&1; then
        warn "Spec gate failed. Adding context and looping back to Phase 1."
        gate_output=$(eval "$SPEC_GATE" 2>&1 || true)

        # The gate failure means something broke at the integration/quality level.
        # We can't directly add tasks — that's the agents' job. Instead, invoke
        # do-task with the failure context so it can diagnose and add fix tasks.
        invoke_agent "do-task" "$DO_MODEL" \
            "The full verification gate ($SPEC_GATE) failed after all tasks were completed. Diagnose the failure, add appropriate fix tasks to plan.md, and address them.

Error output:
$gate_output"

        # Update snapshot so staleness detection works
        prev_snapshot=$(plan_snapshot)
        continue
    fi
    ok "Spec gate passed."

    # ─── Phase 3: Demo ───

    header "Phase 3: run-demo"
    output=$(invoke_agent "run-demo" "$DEMO_MODEL")
    signal=$(extract_signal "$output" "run-demo-status")

    case "$signal" in
        pass)
            ok "run-demo: all demo steps passed."
            ;;
        fail)
            warn "run-demo: demo failed. Tasks added to plan.md. Looping back."
            prev_snapshot=$(plan_snapshot)
            continue
            ;;
        error)
            fail "run-demo: error. Output:"
            echo "$output" | tail -20
            exit 1
            ;;
        *)
            warn "run-demo: unrecognized signal '$signal'. Continuing cautiously."
            ;;
    esac

    # ─── Phase 4: Spec Audit ───

    header "Phase 4: audit-spec"
    output=$(invoke_agent "audit-spec" "$SPEC_MODEL")
    status=$(audit_status)

    case "$status" in
        pass)
            ok "audit-spec: PASS. Spec implementation complete."
            ;;
        fail)
            warn "audit-spec: FAIL. Fix items added to plan.md. Looping back."
            prev_snapshot=$(plan_snapshot)
            continue
            ;;
        *)
            fail "audit-spec: Could not determine status from audit.md. Output:"
            echo "$output" | tail -20
            exit 1
            ;;
    esac

    # ─── Done ───
    break
done

header "Orchestrator Complete"
fanfare
ok "All phases passed. Ready for walk-spec."
ok ""
ok "Next step: run /walk-spec to do the interactive demo walkthrough and submit a PR."
ok "Spec folder: $SPEC_FOLDER"
