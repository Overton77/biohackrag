#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# -------- Defaults (override via flags) --------
PROJECT_ID=""
REGION="us-central1"
REPO="scraper-repo"
IMAGE="dave-podcast-scraper"
JOB_NAME="dave-podcast-scraper"
DOCKER_CONTEXT="."
MONGO_URI="${MONGODB_URI:-}"       # can pass via -u or env
SECRET_NAME="mongo-uri"
BUCKET_NAME=""                     # e.g. "<PROJECT_ID>-dave-scraper-logs"
MOUNT_PATH="/mnt/logs"
LOG_PATH="/mnt/logs/podcast_scraper.log"
CPU="1"
MEMORY="1Gi"
CRON="0 6 * * *"                   # daily at 06:00
TIMEZONE="UTC"                     # e.g. America/New_York
EXECUTE_AFTER_DEPLOY="true"        # set --no-exec to skip

usage() {
  cat <<EOF
Usage: $0 -p <PROJECT_ID> [options]
  -p  PROJECT_ID                      (required)
  -r  REGION                          (default: ${REGION})
  -R  REPO                            (default: ${REPO})
  -i  IMAGE                           (default: ${IMAGE})
  -j  JOB_NAME                        (default: ${JOB_NAME})
  -c  DOCKER_CONTEXT                  (default: ${DOCKER_CONTEXT})
  -u  MONGODB_URI                     (or set env MONGODB_URI)
  -S  SECRET_NAME                     (default: ${SECRET_NAME})
  -b  BUCKET_NAME                     (optional: mount GCS logs bucket)
  -m  MOUNT_PATH                      (default: ${MOUNT_PATH})
  -l  LOG_PATH                        (default: ${LOG_PATH})
  -C  CRON                            (default: "${CRON}")
  -t  TIMEZONE                        (default: ${TIMEZONE})
  --no-exec                           Do not execute job now
  -h|--help                           Show help
Examples:
  $0 -p animated-graph-463101-t5 -u 'mongodb+srv://USER:PASS@...'
  $0 -p animated-graph-463101-t5 -b animated-graph-463101-t5-dave-scraper-logs -t America/New_York -C "0 6 * * *"
EOF
}

# -------- Parse flags --------
while (( "$#" )); do
  case "$1" in
    -p) PROJECT_ID="$2"; shift 2;;
    -r) REGION="$2"; shift 2;;
    -R) REPO="$2"; shift 2;;
    -i) IMAGE="$2"; shift 2;;
    -j) JOB_NAME="$2"; shift 2;;
    -c) DOCKER_CONTEXT="$2"; shift 2;;
    -u) MONGO_URI="$2"; shift 2;;
    -S) SECRET_NAME="$2"; shift 2;;
    -b) BUCKET_NAME="$2"; shift 2;;
    -m) MOUNT_PATH="$2"; shift 2;;
    -l) LOG_PATH="$2"; shift 2;;
    -C) CRON="$2"; shift 2;;
    -t) TIMEZONE="$2"; shift 2;;
    --no-exec) EXECUTE_AFTER_DEPLOY="false"; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown option: $1"; usage; exit 1;;
  esac
done

if [[ -z "$PROJECT_ID" ]]; then echo "ERROR: -p PROJECT_ID is required"; usage; exit 1; fi
if [[ -z "$MONGO_URI" ]]; then
  read -r -p "Enter MongoDB URI (input hidden): " -s MONGO_URI; echo
fi
if [[ -z "$MONGO_URI" ]]; then echo "ERROR: MONGODB_URI cannot be empty"; exit 1; fi
if [[ -n "$BUCKET_NAME" && "${MOUNT_PATH}" != /* ]]; then
  echo "ERROR: MOUNT_PATH must be absolute (starts with /)."; exit 1
fi

echo "== Context =="
echo "Account   : $(gcloud config get-value account 2>/dev/null || true)"
echo "Project   : $PROJECT_ID"
echo "Region    : $REGION"
echo "Repo      : $REPO"
echo "Image     : $IMAGE"
echo "Job       : $JOB_NAME"
echo "Context   : $DOCKER_CONTEXT"
[[ -n "$BUCKET_NAME" ]] && echo "Bucket    : $BUCKET_NAME (mount at $MOUNT_PATH)" || echo "Bucket    : (none)"
echo "Schedule  : $CRON ($TIMEZONE)"

# -------- 1) Enable required services (idempotent) --------
echo "==> Enabling required services (idempotent)…"
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  --project "$PROJECT_ID"

# -------- 2) Ensure Artifact Registry --------
echo "==> Ensuring Artifact Registry repo '$REPO' exists…"
if ! gcloud artifacts repositories describe "$REPO" --location="$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Selenium scraper images" \
    --project "$PROJECT_ID"
fi
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}:latest"

# -------- 3) Build & push image --------
echo "==> Building & pushing image: $IMAGE_URI"
gcloud builds submit "$DOCKER_CONTEXT" --tag "$IMAGE_URI" --project "$PROJECT_ID"

# -------- 4) Secret Manager (create or add version) --------
echo "==> Creating/updating secret '$SECRET_NAME'…"
if gcloud secrets describe "$SECRET_NAME" --project "$PROJECT_ID" >/dev/null 2>&1; then
  printf %s "$MONGO_URI" | gcloud secrets versions add "$SECRET_NAME" --data-file=- --project "$PROJECT_ID"
else
  printf %s "$MONGO_URI" | gcloud secrets create "$SECRET_NAME" --data-file=- --project "$PROJECT_ID"
fi

# Give default compute SA secret access (and Scheduler caller will often need it too)
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
DEFAULT_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEFAULT_SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet

# -------- 5) (Optional) ensure bucket & IAM --------
if [[ -n "$BUCKET_NAME" ]]; then
  echo "==> Ensuring bucket gs://$BUCKET_NAME exists…"
  if ! gsutil ls -b "gs://$BUCKET_NAME" >/dev/null 2>&1; then
    gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://$BUCKET_NAME"
  fi
fi

# -------- 6) Create or update Cloud Run Job --------
echo "==> Creating/updating Cloud Run Job '$JOB_NAME'…"
if gcloud run jobs describe "$JOB_NAME" --region "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud run jobs update "$JOB_NAME" \
    --region "$REGION" --project "$PROJECT_ID" \
    --image "$IMAGE_URI" \
    --cpu "$CPU" --memory "$MEMORY" \
    --set-secrets MONGODB_URI="${SECRET_NAME}:latest" \
    --set-env-vars DB_NAME=biohack_agent,COLLECTION=episodes,LOG_LEVEL=INFO
else
  gcloud run jobs create "$JOB_NAME" \
    --region "$REGION" --project "$PROJECT_ID" \
    --image "$IMAGE_URI" \
    --max-retries=1 \
    --cpu "$CPU" --memory "$MEMORY" \
    --set-secrets MONGODB_URI="${SECRET_NAME}:latest" \
    --set-env-vars DB_NAME=biohack_agent,COLLECTION=episodes,LOG_LEVEL=INFO
fi

# Determine runtime SA (for bucket IAM if needed)
RUN_SA="$(gcloud run jobs describe "$JOB_NAME" --region "$REGION" --project "$PROJECT_ID" --format='value(template.template.serviceAccount)')"
if [[ -z "$RUN_SA" ]]; then RUN_SA="$DEFAULT_SA"; fi

# Mount bucket if provided
if [[ -n "$BUCKET_NAME" ]]; the_]()]()
