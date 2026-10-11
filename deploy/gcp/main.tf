# Google Cloud Run (DEFAULT cloud target). `terraform validate`-checked; review before apply.
#   terraform init && terraform apply -var project_id=<id> -var image=<registry>/aigovops-policy-foundry:<tag>
terraform {
  required_version = ">= 1.6"
  required_providers {
    google = { source = "hashicorp/google", version = ">= 6.0" }
    random = { source = "hashicorp/random", version = ">= 3.6" }
  }
}

variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "us-west1"
}
variable "image" {
  type        = string
  description = "Container image, e.g. us-west1-docker.pkg.dev/<project>/foundry/aigovops-policy-foundry:0.1.0"
}
variable "public" {
  type        = bool
  default     = false
  description = "Allow unauthenticated access. Keep false unless this is a public demo."
}
variable "max_instances" {
  type    = number
  default = 2
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "apis" {
  for_each           = toset(["run.googleapis.com", "artifactregistry.googleapis.com", "secretmanager.googleapis.com"])
  service            = each.key
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "foundry" {
  repository_id = "foundry"
  location      = var.region
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

resource "random_password" "api_token" {
  length  = 40
  special = false
}

resource "google_secret_manager_secret" "api_token" {
  secret_id = "foundry-api-token"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "api_token" {
  secret      = google_secret_manager_secret.api_token.id
  secret_data = random_password.api_token.result
}

resource "google_service_account" "run" {
  account_id   = "policy-foundry"
  display_name = "Policy Foundry runtime (no project roles)"
}

resource "google_secret_manager_secret_iam_member" "run_reads_token" {
  secret_id = google_secret_manager_secret.api_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.run.email}"
}

resource "google_cloud_run_v2_service" "foundry" {
  name                = "policy-foundry"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.run.email
    scaling {
      min_instance_count = 0
      max_instance_count = var.max_instances
    }
    containers {
      image = var.image
      ports {
        container_port = 8000
      }
      resources {
        limits = { cpu = "1", memory = "512Mi" }
      }
      env {
        name = "FOUNDRY_API_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.api_token.secret_id
            version = "latest"
          }
        }
      }
      startup_probe {
        http_get {
          path = "/healthz"
        }
      }
    }
  }
  depends_on = [google_secret_manager_secret_iam_member.run_reads_token]
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  count    = var.public ? 1 : 0
  name     = google_cloud_run_v2_service.foundry.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "url" { value = google_cloud_run_v2_service.foundry.uri }
output "registry" { value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.foundry.repository_id}" }
output "api_token_secret" { value = google_secret_manager_secret.api_token.secret_id }
