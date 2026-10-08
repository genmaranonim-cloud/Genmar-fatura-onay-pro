#!/bin/sh
set -eu

mkdir -p "${PRO_DATA_DIR:-/data/genmar-pro}"

exec litestream replicate -config /etc/litestream.yml \
  -exec "gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 120"
