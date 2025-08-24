Small report (what you did)

APIs enabled
run.googleapis.com, artifactregistry.googleapis.com, cloudbuild.googleapis.com, cloudscheduler.googleapis.com, secretmanager.googleapis.com.

Artifact Registry
Created Docker repo scraper-repo in us-central1.

Secret Manager
Created secret mongo-uri, stored your MONGODB_URI (and fixed quoting in Git Bash).
Granted Secret Accessor to the job’s runtime service account (default compute SA or your custom SA).

Built & pushed image
gcloud builds submit --tag us-central1-docker.pkg.dev/<PROJECT_ID>/scraper-repo/dave-podcast-scraper:latest

Cloud Run Job
Name: dave-podcast-scraper (region us-central1).
CPU 1, Memory 1Gi.
Env vars: DB_NAME=biohack_agent, COLLECTION=episodes, LOG_LEVEL=INFO.
Secret mounted as env: MONGODB_URI = secret:mongo-uri.

(Optional) Logs bucket mount
Bucket: animated-graph-463101-t5-dave-scraper-logs mounted at /mnt/logs, LOG_PATH=/mnt/logs/podcast_scraper.log.
Granted the runtime SA roles/storage.objectUser on the bucket.

Ran the job manually
gcloud run jobs execute dave-podcast-scraper --region us-central1

Still left
Set up Cloud Scheduler to trigger the job daily (e.g., 06:00).
