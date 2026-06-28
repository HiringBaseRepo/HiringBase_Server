#!/bin/sh

WORKER_CMD="taskiq worker app.core.tkq:broker app.main"
SCHEDULER_CMD="taskiq scheduler app.core.tkq:scheduler app.main"
API_CMD="uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"

cleanup() {
  echo "[startup] Cleaning up all processes..."
  for pid in "$WORKER_PID" "$SCHEDULER_PID" "$API_PID"; do
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
}

trap cleanup INT TERM

sh -c "$API_CMD" &
API_PID=$!
echo "[startup] API started with PID $API_PID"

# Worker: auto-restart on crash
(
  while true; do
    echo "[startup] Starting worker..."
    sh -c "$WORKER_CMD"
    EXIT_CODE=$?
    echo "[startup] Worker exited with code $EXIT_CODE. Restarting in 3s..."
    sleep 3
  done
) &
WORKER_PID=$!
echo "[startup] Worker supervisor started with PID $WORKER_PID"

# Scheduler: auto-restart on crash
(
  while true; do
    echo "[startup] Starting scheduler..."
    sh -c "$SCHEDULER_CMD"
    EXIT_CODE=$?
    echo "[startup] Scheduler exited with code $EXIT_CODE. Restarting in 3s..."
    sleep 3
  done
) &
SCHEDULER_PID=$!
echo "[startup] Scheduler supervisor started with PID $SCHEDULER_PID"

# If API dies, shut everything down
wait "$API_PID" 2>/dev/null
echo "[startup] API process died. Shutting down..."
cleanup
exit 1
