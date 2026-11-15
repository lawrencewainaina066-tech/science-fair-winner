#!/bin/sh
set -eu

R2_MOUNTED="false"
FUSE_PID=""

if [ "${SFW_REQUIRE_R2:-false}" = "true" ]; then
  : "${R2_ACCOUNT_ID:?Set the R2_ACCOUNT_ID Worker secret}"
  : "${R2_BUCKET_NAME:?Set the R2_BUCKET_NAME Worker secret}"
  : "${AWS_ACCESS_KEY_ID:?Set the R2 access key as AWS_ACCESS_KEY_ID}"
  : "${AWS_SECRET_ACCESS_KEY:?Set the R2 secret as AWS_SECRET_ACCESS_KEY}"
fi

if [ -n "${R2_ACCOUNT_ID:-}" ] && [ -n "${R2_BUCKET_NAME:-}" ] && \
   [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_SECRET_ACCESS_KEY:-}" ]; then
  mkdir -p /mnt/r2
  echo "Mounting Cloudflare R2 bucket: ${R2_BUCKET_NAME}"
  /usr/local/bin/tigrisfs \
    --endpoint "https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com" \
    --region auto -f "${R2_BUCKET_NAME}" /mnt/r2 &
  FUSE_PID="$!"

  attempt=0
  until mountpoint -q /mnt/r2; do
    if ! kill -0 "$FUSE_PID" 2>/dev/null; then
      echo "R2 FUSE process exited before the bucket mounted." >&2
      exit 1
    fi
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
      echo "Timed out waiting for the R2 bucket mount." >&2
      exit 1
    fi
    sleep 1
  done

  mkdir -p /mnt/r2/projects
  export SFW_PROJECT_DIR=/mnt/r2/projects
  R2_MOUNTED="true"
  echo "SFW project library is using persistent R2 storage."
else
  echo "WARNING: R2 is not configured. Project files will use ephemeral container storage."
fi

streamlit run app.py \
  --server.address=0.0.0.0 \
  --server.port=8501 \
  --server.enableCORS=false &
APP_PID="$!"

cleanup() {
  kill "$APP_PID" 2>/dev/null || true
  if [ "$R2_MOUNTED" = "true" ]; then
    umount /mnt/r2 2>/dev/null || fusermount3 -u /mnt/r2 2>/dev/null || true
    kill "$FUSE_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

wait "$APP_PID"
