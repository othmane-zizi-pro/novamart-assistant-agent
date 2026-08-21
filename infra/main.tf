terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudbuild.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "app" {
  location      = var.region
  repository_id = "novamart"
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

resource "google_service_account" "run" {
  account_id   = "novamart-run"
  display_name = "NovaMart assistant Cloud Run runtime"
}

# The deployed service authenticates to Gemini through the platform backend with
# its service account: no API key exists anywhere in this deployment. The
# google-genai SDK and ADK switch backends purely via the env vars below.
resource "google_project_iam_member" "run_uses_aiplatform" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.run.email}"
}

resource "google_cloud_run_v2_service" "app" {
  name                = "novamart-assistant"
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.run.email
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
    containers {
      image = var.image
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "TRUE"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.gemini_location
      }
      startup_probe {
        http_get {
          path = "/api/healthz"
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 24
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_project_iam_member.run_uses_aiplatform,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.app.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
