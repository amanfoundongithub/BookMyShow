#!/usr/bin/env bash
set -euo pipefail

# Run from any directory with: ./scripts/dev.sh
# Requires the repo .venv, a configured root .env, and local Redis/RabbitMQ.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
HOST="${DEV_HOST:-127.0.0.1}"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
    echo "Missing $ROOT_DIR/.env" >&2
    exit 1
fi

if [[ ! -x "$PYTHON" ]]; then
    echo "Python executable not found: $PYTHON" >&2
    echo "Create the repo virtual environment or set PYTHON=/path/to/python." >&2
    exit 1
fi

PIDS=()

cleanup() {
    local pid
    trap - EXIT INT TERM
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    for pid in "${PIDS[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

start_api() {
    local name="$1"
    local service_dir="$2"
    local port="$3"

    echo "Starting $name on http://$HOST:$port"
    (
        cd "$ROOT_DIR"
        PYTHONPATH="$service_dir${PYTHONPATH:+:$PYTHONPATH}" \
            "$PYTHON" -m uvicorn app.main:app \
            --reload --reload-dir "$service_dir" --host "$HOST" --port "$port"
    ) &
    PIDS+=("$!")
}

start_api "user" "$ROOT_DIR/services/user" "${USER_SERVICE_PORT:-8004}"
start_api "gateway" "$ROOT_DIR/gateway" "${GATEWAY_PORT:-8000}"
start_api "catalog" "$ROOT_DIR/services/catalog" "${CATALOG_PORT:-8001}"
start_api "booking" "$ROOT_DIR/services/booking" "${BOOKING_PORT:-8002}"
start_api "payment" "$ROOT_DIR/services/payment" "${PAYMENT_PORT:-8003}"

echo "Starting notification worker (RabbitMQ consumer)"
(
    cd "$ROOT_DIR"
    PYTHONPATH="$ROOT_DIR/services/notification${PYTHONPATH:+:$PYTHONPATH}" \
        "$PYTHON" -m app.worker
) &
PIDS+=("$!")

echo "All processes started. Press Ctrl-C to stop them."
wait
