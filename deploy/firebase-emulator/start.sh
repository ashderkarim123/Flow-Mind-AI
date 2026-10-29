#!/bin/sh
# Starts the Auth + Firestore emulators. Users and data are saved to /data when the container
# stops normally (docker compose stop / down) and loaded again on the next start.
set -e

IMPORT=""
if [ -d /data/firestore_export ]; then
  IMPORT="--import /data"
fi

# "demo-" projects never talk to real Google services
exec firebase emulators:start \
  --only auth,firestore \
  --project "${FIREBASE_PROJECT_ID:-demo-flowmind}" \
  $IMPORT \
  --export-on-exit /data
