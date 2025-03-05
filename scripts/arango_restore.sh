#!/bin/bash
# arangorestore_db.sh

# --- Logging Function ---
log() {
    printf "[%s] %s\n" "$(date +%T)" "$*" >&2
}

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"  # Get script's directory

DB_NAME="fraud_detection"
TARGET_DB=${DB_NAME} 

DUMPS_ROOT="backups/fraud_detection"
CONTAINER_NAME="arangodb"
ARANGO_USER="root"
ARANGO_PASS="openSesame"
CONTAINER_TMP_DIR="/tmp/arangorestore"

# --- Arguments ---
# First find latest directory, then validate it
LATEST_DUMP=$(find "${DUMPS_ROOT}" -mindepth 1 -maxdepth 1 -type d | sort -r | head -1)

# --- Validation ---
log "🔍 Checking dumps in: ${DUMPS_ROOT}"

if [ ! -d "${LATEST_DUMP}" ]; then
  log "❌ No dumps found in: ${DUMPS_ROOT}"
  exit 1
fi

if [ ! -d "${LATEST_DUMP}/arangodump" ]; then
  log "❌ Invalid dump structure in ${LATEST_DUMP}"
  log "    Missing: ${LATEST_DUMP}/arangodump subdirectory"
  log "    Directory contents:"
  ls -l "${LATEST_DUMP}" | sed 's/^/      /' >&2
  exit 1
fi

log "✅ Selected dump: ${LATEST_DUMP}"

# Validate dump structure
if [ ! -f "${LATEST_DUMP}/arangodump/ENCRYPTION" ]; then
  echo "ERROR: Not a valid ArangoDB dump directory" >&2
  exit 1
fi

log "🚀 Starting restore to database '${TARGET_DB}'"
log "🔍 Using dump: ${LATEST_DUMP} (exists: $(test -d "$LATEST_DUMP" && echo ✅ || echo ❌))"

# Copy to container
log "📦 Copying dump to container: ${CONTAINER_TMP_DIR}..."
docker cp "${LATEST_DUMP}" "${CONTAINER_NAME}:${CONTAINER_TMP_DIR}" || {
    log "❌ Failed to copy dump files"; exit 1;
}

# Prepare restore command
RESTORE_PATH="${CONTAINER_TMP_DIR}/$(basename "${LATEST_DUMP}")/arangodump"
RESTORE_CMD="arangorestore \
  --server.endpoint tcp://localhost:8529 \
  --server.username ${ARANGO_USER} \
  --server.password ${ARANGO_PASS} \
  --server.database ${TARGET_DB} \
  --input-directory ${RESTORE_PATH} \
  --overwrite true \
  --create-database true"

# Execute restore
log "🚀 Executing restore from: ${RESTORE_PATH}"
if docker exec "${CONTAINER_NAME}" ${RESTORE_CMD}; then
    log "🧹 Cleanup: Removing temp files"
    docker exec "${CONTAINER_NAME}" rm -rf "${CONTAINER_TMP_DIR}"
    log "✅ Restore successful"
else
    log "💥 Restore failed!"
    log "⚠️  Temp files preserved at: ${CONTAINER_TMP_DIR}"
    exit 1
fi