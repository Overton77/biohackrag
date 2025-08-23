#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# --- Defaults (override via flags or env) ---
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
JOB_NAME="${JOB_NAME:-dave-podcast-scraper}"
BUCKET_NAME="${BUCKET_NAME:-}"             # e.g. "$PROJECT_ID-dave-scraper-logs"
MOUNT_PATH="${MOUNT_PATH:-/mnt/logs}"
LOG_PATH="${LOG_PATH:-/mnt/logs/podcast_scraper.log}"

usage() {
  cat <<EOF
Usage: $0 -p <PROJECT_ID> -r <REGION> -j <JOB_NAME> -b <BUCKET_NAME> [-m <MOUNT_PATH>] [-l <LOG_PATH>]

Example:
  $0 -p animated-graph-463101-t5 -r us-central1 -j dave-podcast-scraper -b animated-graph-463101-t5-dave-scraper-logs

Notes:
- Uses --project on all gcloud commands (no config confusion).
- Quotes the comma-separated flags to avoid Git Bash parsing issues.
EOF
}

# --- Parse flags ---
while (( "$#" )); do
  case "$1" in
    -p) PROJECT_ID="$2"; shift 2 ;;
    -r) REGION="$2"; shift 2 ;;
    -j) JOB_NAME="$2"; shift 2 ;;
    -b) BUCKET_NAME="$2"; shift 2 ;;
    -m) MOUNT_PATH="$2"; shift 2 ;;
    -l) LOG_PATH="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 1 ;;
  esac
done

if [[ -z "${PROJECT_ID}" || -z "${BUCKET_NAME}" ]]; then
  echo "ERROR: PROJECT_ID and BUCKET_NAME are required."; usage; exit 1
fi

if [[ "${MOUNT_PATH}" != /* ]]; then
  echo "ERROR: MOUNT_PATH must be an absolute unix path (starts with /). Got: '${MOUNT_PATH}'"
  exit 1
fi

echo "Account : $(gcloud config get-value account 2>/dev/null || true)"
echo "Project : ${PROJECT_ID}"
echo "Region  : ${REGION}"
echo "Job     : ${JOB_NAME}"
echo "Bucket  : ${BUCKET_NAME}"
echo "Mount   : ${MOUNT_PATH}"
echo "LOG_PATH: ${LOG_PATH}"

# 1) Ensure job exists (fast fail if not)
gcloud run jobs describe "${JOB_NAME}" --region "${REGION}" --project "${PROJECT_ID}" >/dev/null

# 2) Ensure bucket exists (no-op if already there)
if ! gsutil ls -b "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
  echo "Bucket gs://${BUCKET_NAME} not found; creating…"
  gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${BUCKET_NAME}"
fi

# 3) Figure out which SA the job uses (or fallback to default compute SA)
RUN_SA="$(gcloud run jobs describe "${JOB_NAME}" \
  --region "${REGION}" --project "${PROJECT_ID}" \
  --format='value(template.template.serviceAccount)')"

if [[ -z "${RUN_SA}" ]]; then
  PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
  RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
fi
echo "Runtime SA: ${RUN_SA}"

# 4) Grant bucket write access to the runtime SA (objectUser is enough to write logs)
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${RUN_SA}" \
  --role="roles/storage.objectUser" \
  --project "${PROJECT_ID}"

# 5) Clear any previous volumes/mounts (idempotent)
gcloud run jobs update "${JOB_NAME}" \
  --region "${REGION}" --project "${PROJECT_ID}" \
  --clear-volumes --clear-volume-mounts

# 6) Re-add the Cloud Storage volume + mount (quotes avoid Git Bash issues with commas)
gcloud run jobs update "${JOB_NAME}" \
  --region "${REGION}" --project "${PROJECT_ID}" \
  "--add-volume=name=logs,type=cloud-storage,bucket=${BUCKET_NAME}" \
  "--add-volume-mount=volume=logs,mount-path=${MOUNT_PATH}" \
  "--set-env-vars=LOG_PATH=${LOG_PATH}"

# 7) Show what’s configured
echo
echo "Current mounts/volumes:"
gcloud run jobs describe "${JOB_NAME}" --region "${REGION}" --project "${PROJECT_ID}" \
  --format='yaml(template.template.containers[0].volumeMounts,template.volumes)'

echo
echo "✅ Mount update complete."
