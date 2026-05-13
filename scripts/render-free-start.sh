#!/bin/sh

set -eu

WORKER_CMD="taskiq worker app.core.tkq:broker app.main:app"
API_CMD="uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"

cleanup() {
  if [ -n "${API_PID:-}" ] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
  fi
  if [ -n "${WORKER_PID:-}" ] && kill -0 "$WORKER_PID" 2>/dev/null; then
    kill "$WORKER_PID" 2>/dev/null || true
  fi
}

trap cleanup INT TERM EXIT

sh -c "$WORKER_CMD" &
WORKER_PID=$!

sh -c "$API_CMD" &
API_PID=$!

while kill -0 "$API_PID" 2>/dev/null && kill -0 "$WORKER_PID" 2>/dev/null; do
  sleep 5
done

if ! kill -0 "$API_PID" 2>/dev/null; then
  wait "$API_PID" || true
  exit 1
fi

if ! kill -0 "$WORKER_PID" 2>/dev/null; then
  wait "$WORKER_PID" || true
  kill "$API_PID" 2>/dev/null || true
  wait "$API_PID" || true
  exit 1
fi
