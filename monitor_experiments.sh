#!/usr/bin/env bash
# monitor_experiments.sh
# Real-time monitor for run_batch_experiments.py
# Usage: ./monitor_experiments.sh [LOG_FILE]
#
# If no log file is given it automatically picks the latest batch_runner log.

set -euo pipefail

LOG_DIR="logs"
REFRESH_INTERVAL=2  # seconds between header re-prints in follow mode

# ── colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# ── pick log file ─────────────────────────────────────────────────────────────
if [[ $# -ge 1 ]]; then
    LOG_FILE="$1"
else
    # Find the most recently modified batch_runner log
    LOG_FILE=$(ls -t "${LOG_DIR}"/batch_runner_*.log 2>/dev/null | head -n1 || true)
fi

if [[ -z "${LOG_FILE}" ]]; then
    echo -e "${RED}No batch_runner log found in ${LOG_DIR}/${RESET}"
    echo "Start the batch runner first:"
    echo "  sudo python3 run_batch_experiments.py --type quick"
    exit 1
fi

if [[ ! -f "${LOG_FILE}" ]]; then
    echo -e "${RED}Log file not found: ${LOG_FILE}${RESET}"
    exit 1
fi

# ── helper: colour a line based on its content ────────────────────────────────
colorise_line() {
    local line="$1"
    if   echo "$line" | grep -qE "\[OK\]|completed|BATCH COMPLETE";    then echo -e "${GREEN}${line}${RESET}"
    elif echo "$line" | grep -qE "\[FAIL\]|\[ERROR\]|error|Error";      then echo -e "${RED}${line}${RESET}"
    elif echo "$line" | grep -qE "\[TIMEOUT\]|timed out";               then echo -e "${RED}${line}${RESET}"
    elif echo "$line" | grep -qE "WARNING|Warning|\[SKIP\]|skipped";    then echo -e "${YELLOW}${line}${RESET}"
    elif echo "$line" | grep -qE "EXPERIMENT [0-9]+/[0-9]+|Progress:";  then echo -e "${CYAN}${BOLD}${line}${RESET}"
    elif echo "$line" | grep -qE "^=+$|^-+$";                           then echo -e "${BLUE}${line}${RESET}"
    else echo "${line}"
    fi
}

# ── header ────────────────────────────────────────────────────────────────────
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}╔══════════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}${BLUE}║           Adaptive Routing Batch Experiment Monitor                  ║${RESET}"
    echo -e "${BOLD}${BLUE}╚══════════════════════════════════════════════════════════════════════╝${RESET}"
    echo -e "  Log file : ${CYAN}${LOG_FILE}${RESET}"
    echo -e "  Time     : $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "  Ctrl+C to stop monitoring (experiments keep running)"
    echo ""
}

# ── quick stats extracted from the log so far ─────────────────────────────────
print_stats() {
    local log="$1"
    local total completed failed progress

    total=$(grep -c "^INFO - batch_runner - EXPERIMENT [0-9]" "$log" 2>/dev/null || echo 0)
    completed=$(grep -c "\[OK\]" "$log" 2>/dev/null || echo 0)
    failed=$(grep -c "\[FAIL\]\|\[TIMEOUT\]\|\[ERROR\]" "$log" 2>/dev/null || echo 0)

    # Last progress line
    progress=$(grep "Progress:" "$log" 2>/dev/null | tail -n1 || true)

    echo -e "${BOLD}  Quick Stats:${RESET}"
    echo -e "    Experiments seen : ${total}"
    echo -e "    ${GREEN}Completed        : ${completed}${RESET}"
    echo -e "    ${RED}Failed/Timeout   : ${failed}${RESET}"
    if [[ -n "$progress" ]]; then
        echo -e "    ${CYAN}${progress}${RESET}"
    fi
    echo ""
}

# ── mode: show last N lines then follow ───────────────────────────────────────
TAIL_LINES=40

print_header
echo -e "${BOLD}=== Last ${TAIL_LINES} lines of log ===${RESET}"
echo ""

# Colour the historical tail
while IFS= read -r line; do
    colorise_line "$line"
done < <(tail -n "$TAIL_LINES" "$LOG_FILE")

echo ""
print_stats "$LOG_FILE"
echo -e "${BOLD}=== Following log (live) — Ctrl+C to quit ===${RESET}"
echo ""

# Live follow
tail -F -n0 "$LOG_FILE" | while IFS= read -r line; do
    colorise_line "$line"
done
