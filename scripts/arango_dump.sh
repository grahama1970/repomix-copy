#!/bin/bash
# arangodump_db.sh
# This script dumps an ArangoDB database from a Docker container with a low memory batch size.
#
# Usage: ./arangodump_db.sh
# Make sure arangodump is in your PATH.
# This script dumps an ArangoDB database from a Docker container with a low memory batch size.
# The dump path follows the structure: backups/<database_name>/<timestamp>/arangodump
#
# Usage: ./arangodump_db.sh
# Make sure arangodump is in your PATH.

# --- Configuration ---
CONTAINER_NAME="arangodb"  # Update with your container name
ARANGO_USER="root"
ARANGO_PASS="openSesame"
DB_NAME="verifaix"
HOST_DUMP_DIR="./arangodb_dumps"  # New host directory for all dumps
CONTAINER_DUMP_DIR="/tmp/arangodump"  # Temporary container directory

# Set a low batch size to limit memory usage (adjust as needed)
BATCH_SIZE=100

# Create timestamped dump directory
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DUMP_DIR="${HOST_DUMP_DIR}/${DB_NAME}_${TIMESTAMP}"
mkdir -p "${DUMP_DIR}"

echo "Dumping ArangoDB database '${DB_NAME}' from container ${CONTAINER_NAME}..."
echo "Using batch size: ${BATCH_SIZE}"
echo "Output directory: ${DUMP_DIR}"

# Execute dump inside container and copy results out
docker exec "${CONTAINER_NAME}" \
  arangodump \
  --server.endpoint "tcp://localhost:8529" \
  --server.username "${ARANGO_USER}" \
  --server.password "${ARANGO_PASS}" \
  --server.database "${DB_NAME}" \
  --output-directory "${CONTAINER_DUMP_DIR}" \
  --batch-size "${BATCH_SIZE}" \
  --overwrite true

# Check if dump succeeded before copying
if [ $? -eq 0 ]; then
  echo "Copying dump from container..."
  docker cp "${CONTAINER_NAME}:${CONTAINER_DUMP_DIR}" "${DUMP_DIR}"
  docker exec "${CONTAINER_NAME}" rm -rf "${CONTAINER_DUMP_DIR}"
  echo "Database dump completed successfully."
else
  echo "Database dump failed." >&2
  exit 1
fi
