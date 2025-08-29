#!/usr/bin/env bash
set -euo pipefail

# --- Config (override with env vars) ---
PROJECT_ID="${PROJECT_ID:-animated-graph-463101-t5}"
REGION="${REGION:-us-central1}"
JOB_NAME="${JOB_NAME:-episode-enhancer}"
IMAGE="gcr.io/${PROJECT_ID}/episode-enhancer"
FASTAPI_SA="${FASTAPI_SA:-fastapi-sa@${PROJECT_ID}.iam.gserviceaccount.com}"

echo ">> Enabling required APIs (idempotent)"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com --project "${PROJECT_ID}"

echo ">> Building with custom Dockerfile: /Dockerfile.job (context: repo root)"
gcloud builds submit \
  --tag "${IMAGE}" \
  --file Dockerfile.job \
  --project "${PROJECT_ID}" \
  .

echo ">> Creating/updating Cloud Run Job: ${JOB_NAME}"
set +e
gcloud run jobs describe "${JOB_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" >/dev/null 2>&1
EXISTS=$?
set -e

COMMON_FLAGS=(
  --image "${IMAGE}"
  --region "${REGION}"
  --task-timeout=3600
  --max-retries=1
  --cpu=1
  --memory=512Mi
  --set-env-vars=PYTHONUNBUFFERED=1
)

if [[ "${EXISTS}" -ne 0 ]]; then
  gcloud run jobs create "${JOB_NAME}" "${COMMON_FLAGS[@]}" --project "${PROJECT_ID}"
else
  gcloud run jobs update "${JOB_NAME}" "${COMMON_FLAGS[@]}" --project "${PROJECT_ID}"
fi

echo ">> Granting FastAPI service account permission to run the job"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member "serviceAccount:${FASTAPI_SA}" \
  --role "roles/run.developer" \
  --quiet

echo "✅ Done. Image: ${IMAGE}, Job: ${JOB_NAME} in ${REGION}"
echo "Tip: set DB/Firecrawl env vars on the job with --set-env-vars KEY=VAL,... in COMMON_FLAGS."
