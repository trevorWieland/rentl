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
#
#   Per-command CLI and model (implementation vs audit use different tools):
#     ORCH_CLI           - Fallback CLI for implementation commands (default: "claude -p --dangerously-skip-permissions")
#     ORCH_DO_CLI        - CLI for do-task (default: ORCH_CLI)
#     ORCH_AUDIT_CLI     - CLI for audit-task (default: "codex exec --yolo")
#     ORCH_DEMO_CLI      - CLI for run-demo (default: ORCH_CLI)
#     ORCH_SPEC_CLI      - CLI for audit-spec (default: "codex exec --yolo")
#     ORCH_DO_MODEL      - Model for do-task (default: "sonnet")
#     ORCH_AUDIT_MODEL   - Model for audit-task (default: "gpt-5.3-codex")
#     ORCH_DEMO_MODEL    - Model for run-demo (default: "sonnet")
#     ORCH_SPEC_MODEL    - Model for audit-spec (default: "gpt-5.3-codex")
#
#   Gates and limits:
#     ORCH_TASK_GATE     - Task-level verification command (default: "make check")
#     ORCH_SPEC_GATE     - Spec-level verification command (default: "make all")
#     ORCH_MAX_CYCLES    - Safety limit on full cycles (default: 10, staleness detector is primary)
#     ORCH_COMMANDS_DIR  - Path to command markdown files (default: ".claude/commands/agent-os")

set -euo pipefail

# --- Colors and formatting ---

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

# tty-safe printf — all UI output goes to /dev/tty so it's never captured by $()
tput() { printf "$@" > /dev/tty 2>/dev/null; }

# Only used for fatal errors that should stop the script
fail() { echo -e "${RED}[orch]${NC} $*"; }

# Play the victory fanfare (best-effort, never blocks on failure)
fanfare() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local wav="$script_dir/fanfare.wav"
    if [[ ! -f "$wav" ]]; then return; fi

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

# --- Progress display ---

SCRIPT_START=$(date +%s)
TIMER_PID=""

SPINNER=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")

cleanup_timer() {
    if [[ -n "$TIMER_PID" ]]; then
        kill "$TIMER_PID" 2>/dev/null || true
        wait "$TIMER_PID" 2>/dev/null || true
        TIMER_PID=""
    fi
}
trap cleanup_timer EXIT INT TERM

_timer_loop() {
    local label="$1" model="$2" start_ts="$3"
    local i=0
    while true; do
        local now elapsed mins secs frame
        now=$(date +%s)
        elapsed=$((now - start_ts))
        mins=$((elapsed / 60))
        secs=$((elapsed % 60))
        frame="${SPINNER[$((i % ${#SPINNER[@]}))]}"
        if [[ -n "$model" ]]; then
            printf "\r  ${BLUE}%s${NC} %-14s │ %-16s │ %dm %02ds" \
                "$frame" "$label" "$model" "$mins" "$secs" > /dev/tty 2>/dev/null
        else
            printf "\r  ${BLUE}%s${NC} %-14s │ %dm %02ds" \
                "$frame" "$label" "$mins" "$secs" > /dev/tty 2>/dev/null
        fi
        i=$((i + 1))
        sleep 1
    done
}

begin_phase() {
    local label="$1" model="${2:-}"
    _PHASE_START=$(date +%s)
    _PHASE_LABEL="$label"
    # Redirect stdout/stderr to /dev/null so the background timer doesn't
    # inherit the pipe fd from $(invoke_agent ...) — without this, the
    # command substitution blocks forever waiting for the timer to close the fd.
    _timer_loop "$label" "$model" "$_PHASE_START" > /dev/null 2>&1 &
    TIMER_PID=$!
}

end_phase() {
    local status="${1:-ok}" annotation="${2:-}"
    cleanup_timer

    local elapsed mins secs
    elapsed=$(( $(date +%s) - _PHASE_START ))
    mins=$((elapsed / 60))
    secs=$((elapsed % 60))

    local suffix=""
    if [[ -n "$annotation" ]]; then
        suffix=" · ${annotation}"
    fi

    printf "\r\033[K" > /dev/tty 2>/dev/null
    if [[ "$status" == "ok" ]]; then
        printf "  ${GREEN}✓${NC} %-14s │ %dm %02ds%s\n" "$_PHASE_LABEL" "$mins" "$secs" "$suffix" > /dev/tty 2>/dev/null
    else
        printf "  ${RED}✗${NC} %-14s │ %dm %02ds%s\n" "$_PHASE_LABEL" "$mins" "$secs" "$suffix" > /dev/tty 2>/dev/null
    fi
}

# --- Configuration ---

SPEC_FOLDER="${1:?Usage: orchestrate.sh <spec-folder>}"
shift

# Defaults — implementation uses Claude, auditing uses Codex (different model = independent review)
_DEFAULT_CLI="${ORCH_CLI:-claude -p --dangerously-skip-permissions}"
DO_CLI="${ORCH_DO_CLI:-$_DEFAULT_CLI}"
DO_MODEL="${ORCH_DO_MODEL:-sonnet}"
AUDIT_CLI="${ORCH_AUDIT_CLI:-codex exec --yolo}"
AUDIT_MODEL="${ORCH_AUDIT_MODEL:-gpt-5.3-codex}"
DEMO_CLI="${ORCH_DEMO_CLI:-$_DEFAULT_CLI}"
DEMO_MODEL="${ORCH_DEMO_MODEL:-sonnet}"
SPEC_CLI="${ORCH_SPEC_CLI:-codex exec --yolo}"
SPEC_MODEL="${ORCH_SPEC_MODEL:-gpt-5.3-codex}"
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

next_task_label() {
    local line
    line=$(grep -m1 -P '^\s*- \[ \] Task \d+' "$SPEC_FOLDER/plan.md" 2>/dev/null) || true
    if [[ -n "$line" ]]; then
        echo "$line" | sed 's/^\s*- \[ \] //'
    else
        echo ""
    fi
}

invoke_agent() {
    local command_name="$1"
    local cli="$2"
    local model="$3"
    local extra_context="${4:-}"

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

    local cmd="$cli"
    if [[ -n "$model" ]]; then
        cmd="$cmd --model $model"
    fi

    # NOTE: caller must call begin_phase before and end_phase after.
    # begin_phase cannot run here because $(invoke_agent ...) is a subshell
    # and _PHASE_START would be lost when the subshell exits.

    local output

    if [[ "$cli" == *codex* ]]; then
        local last_msg_file
        last_msg_file=$(mktemp)
        eval "$cmd -o '$last_msg_file'" <<< "$prompt" > /dev/null 2>&1 || true
        if [[ -s "$last_msg_file" ]]; then
            output=$(cat "$last_msg_file")
        else
            output=""
        fi
        rm -f "$last_msg_file"
    else
        output=$(eval "$cmd" <<< "$prompt" 2>&1) || true
    fi

    echo "$output"
}

# Run a gate command silently with spinner. Output stored in LAST_GATE_OUTPUT.
LAST_GATE_OUTPUT=""
run_gate() {
    local label="$1"
    local gate_cmd="$2"

    begin_phase "$label"

    local exit_code
    LAST_GATE_OUTPUT=$(eval "$gate_cmd" 2>&1) && exit_code=0 || exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        end_phase "ok"
    else
        end_phase "fail"
    fi

    return $exit_code
}

extract_signal() {
    local output="$1"
    local prefix="$2"
    echo "$output" | grep -oP "${prefix}: \K\w[\w-]*" | tail -1 || true
}

count_unchecked() {
    grep -cP '^\s*- \[ \]' "$SPEC_FOLDER/plan.md" 2>/dev/null || echo "0"
}

plan_snapshot() {
    md5sum "$SPEC_FOLDER/plan.md" 2>/dev/null | cut -d' ' -f1 || true
}

audit_status() {
    head -1 "$SPEC_FOLDER/audit.md" 2>/dev/null | grep -oP 'status: \K\w+' || echo "unknown"
}

MAX_GATE_RETRIES=3

# --- Main loop ---

tput "\n${BOLD}═══ Orchestrator ═══${NC}\n\n"
tput "  ${DIM}Spec:${NC}    %s\n" "$SPEC_FOLDER"
tput "  ${DIM}Impl:${NC}    %s ${DIM}(%s)${NC}\n" "$DO_MODEL" "${DO_CLI%% *}"
tput "  ${DIM}Audit:${NC}   %s ${DIM}(%s)${NC}\n" "$AUDIT_MODEL" "${AUDIT_CLI%% *}"
tput "  ${DIM}Gates:${NC}   %s │ %s\n" "$TASK_GATE" "$SPEC_GATE"

cycle=0
prev_snapshot=""
stale_count=0
STALE_LIMIT=3

while true; do
    cycle=$((cycle + 1))

    if [[ $cycle -gt $MAX_CYCLES ]]; then
        fail "Safety limit reached ($MAX_CYCLES cycles)."
        exit 1
    fi

    # Staleness detection
    current_snapshot=$(plan_snapshot)
    if [[ -n "$prev_snapshot" && "$current_snapshot" == "$prev_snapshot" ]]; then
        stale_count=$((stale_count + 1))
        if [[ $stale_count -ge $STALE_LIMIT ]]; then
            fail "Stale — plan.md unchanged for $stale_count cycles. See signposts.md / audit-log.md."
            exit 1
        fi
        tput "  ${YELLOW}⚠ plan.md unchanged (%d/%d)${NC}\n" "$stale_count" "$STALE_LIMIT"
    else
        stale_count=0
    fi
    prev_snapshot="$current_snapshot"

    tput "\n${BOLD}── Cycle %d ──${NC} %d tasks remaining\n" "$cycle" "$(count_unchecked)"

    # ─── Phase 1: Task Loop ───

    while true; do
        unchecked=$(count_unchecked)
        if [[ "$unchecked" -eq 0 ]]; then
            break
        fi

        task_label=$(next_task_label)
        if [[ -n "$task_label" ]]; then
            tput "\n  ${BOLD}► %s${NC}\n" "$task_label"
        fi

        # do-task
        begin_phase "do-task" "$DO_MODEL"
        output=$(invoke_agent "do-task" "$DO_CLI" "$DO_MODEL")
        signal=$(extract_signal "$output" "do-task-status")

        case "$signal" in
            complete)
                end_phase "ok" "task completed"
                ;;
            all-done)
                end_phase "ok" "all tasks done"
                break
                ;;
            blocked)
                end_phase "fail" "blocked"
                fail "Human intervention needed. See signposts.md."
                exit 1
                ;;
            error)
                end_phase "fail" "error"
                echo "$output" | tail -20
                exit 1
                ;;
            *)
                end_phase "ok" "signal: ${signal:-none}"
                ;;
        esac

        # Task gate with retry loop
        gate_attempt=0
        gate_passed=false

        while [[ "$gate_passed" == "false" ]]; do
            gate_attempt=$((gate_attempt + 1))

            if run_gate "make check" "$TASK_GATE"; then
                gate_passed=true
            else
                if [[ $gate_attempt -ge $MAX_GATE_RETRIES ]]; then
                    fail "Task gate failing after $MAX_GATE_RETRIES attempts:"
                    echo "$LAST_GATE_OUTPUT" | tail -30
                    exit 1
                fi

                # Re-invoke do-task with gate errors
                begin_phase "do-task" "$DO_MODEL"
                output=$(invoke_agent "do-task" "$DO_CLI" "$DO_MODEL" \
                    "GATE FAILURE — '$TASK_GATE' FAILED. Fix these errors, run the gate yourself, then exit with do-task-status: complete.

\`\`\`
$LAST_GATE_OUTPUT
\`\`\`")
                signal=$(extract_signal "$output" "do-task-status")
                end_phase "ok" "gate fix"

                if [[ "$signal" == "blocked" || "$signal" == "error" ]]; then
                    fail "do-task: '$signal' while fixing gate. See signposts.md."
                    exit 1
                fi
            fi
        done

        # audit-task
        begin_phase "audit-task" "$AUDIT_MODEL"
        output=$(invoke_agent "audit-task" "$AUDIT_CLI" "$AUDIT_MODEL")
        signal=$(extract_signal "$output" "audit-task-status")

        case "$signal" in
            pass)
                end_phase "ok" "passed"
                ;;
            fail)
                end_phase "ok" "issues found — fix items added"
                ;;
            error)
                end_phase "fail" "error"
                echo "$output" | tail -20
                exit 1
                ;;
            *)
                end_phase "ok" "signal: ${signal:-none}"
                ;;
        esac
    done

    # ─── Phase 2: Spec Gate ───

    if ! run_gate "make all" "$SPEC_GATE"; then
        tput "  ${YELLOW}↳ spec gate failed, invoking do-task to fix${NC}\n"
        begin_phase "do-task" "$DO_MODEL"
        output=$(invoke_agent "do-task" "$DO_CLI" "$DO_MODEL" \
            "The full verification gate ($SPEC_GATE) failed after all tasks were completed. Diagnose and fix.

\`\`\`
$LAST_GATE_OUTPUT
\`\`\`")
        end_phase "ok" "gate fix applied"
        continue
    fi

    # ─── Phase 3: Demo ───

    begin_phase "run-demo" "$DEMO_MODEL"
    output=$(invoke_agent "run-demo" "$DEMO_CLI" "$DEMO_MODEL")
    signal=$(extract_signal "$output" "run-demo-status")

    case "$signal" in
        pass)
            end_phase "ok" "all steps passed"
            ;;
        fail)
            end_phase "ok" "failed — fix tasks added"
            continue
            ;;
        error)
            end_phase "fail" "error"
            echo "$output" | tail -20
            exit 1
            ;;
        *)
            end_phase "ok" "signal: ${signal:-none}"
            ;;
    esac

    # ─── Phase 4: Spec Audit ───

    begin_phase "audit-spec" "$SPEC_MODEL"
    output=$(invoke_agent "audit-spec" "$SPEC_CLI" "$SPEC_MODEL")
    status=$(audit_status)

    case "$status" in
        pass)
            end_phase "ok" "PASS"
            ;;
        fail)
            end_phase "ok" "FAIL — fix items added"
            continue
            ;;
        *)
            end_phase "fail" "unknown status"
            echo "$output" | tail -20
            exit 1
            ;;
    esac

    break
done

# ─── Done ───

fanfare

total_elapsed=$(( $(date +%s) - SCRIPT_START ))
total_mins=$((total_elapsed / 60))
total_secs=$((total_elapsed % 60))

tput "\n${GREEN}${BOLD}═══ Complete ═══${NC} %dm %02ds\n\n" "$total_mins" "$total_secs"
tput "  Next: run ${BOLD}/walk-spec${NC} for interactive demo + PR\n"
tput "  Spec: %s\n\n" "$SPEC_FOLDER"
