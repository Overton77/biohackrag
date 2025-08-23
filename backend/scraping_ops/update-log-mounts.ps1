Param(
  [string]$Region     = $(if ($env:REGION) {$env:REGION} else {"us-central1"}),
  [string]$ProjectId  = $(if ($env:PROJECT_ID) {$env:PROJECT_ID} else { (gcloud config get-value project) }),
  [string]$JobName    = "dave-podcast-scraper",
  [string]$BucketName = $null,  # e.g. "$env:PROJECT_ID-dave-scraper-logs"
  [string]$MountPath  = "/mnt/logs",
  [string]$LogPath    = "/mnt/logs/podcast_scraper.log"
)

if (-not $BucketName) {
  $BucketName = "$ProjectId-dave-scraper-logs"
}

Write-Host "Region      : $Region"
Write-Host "Project     : $ProjectId"
Write-Host "Job         : $JobName"
Write-Host "Bucket      : $BucketName"
Write-Host "Mount Path  : $MountPath"
Write-Host "Log Path    : $LogPath"

# Clear any prior mounts first (idempotent)
gcloud run jobs update $JobName --region $Region --clear-volumes --clear-volume-mounts | Out-Null

# Re-add the Cloud Storage mount
$addVol      = "name=logs,type=cloud-storage,bucket=$BucketName"
$addVolMount = "volume=logs,mount-path=$MountPath"

gcloud run jobs update $JobName `
  --region $Region `
  --add-volume=$addVol `
  --add-volume-mount=$addVolMount `
  --set-env-vars=LOG_PATH=$LogPath

# Show what’s configured
gcloud run jobs describe $JobName --region $Region `
  --format 'yaml(template.template.containers[0].volumeMounts,template.volumes)'
