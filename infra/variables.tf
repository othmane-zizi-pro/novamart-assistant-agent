variable "project_id" {
  description = "GCP project to deploy into"
  type        = string
}

variable "region" {
  description = "Deployment region for Cloud Run and Artifact Registry"
  type        = string
  default     = "us-central1"
}

variable "gemini_location" {
  description = "Serving location for Gemini publisher models; the newest models publish to global only"
  type        = string
  default     = "global"
}

variable "image" {
  description = "Full Artifact Registry image reference for the service"
  type        = string
}
