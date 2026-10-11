# Azure Container Apps. `terraform validate`-checked; review before apply.
#   terraform init && terraform apply -var subscription_id=<id> -var image=<registry>/aigovops-policy-foundry:<tag>
terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = ">= 4.0" }
    random  = { source = "hashicorp/random", version = ">= 3.6" }
  }
}

variable "subscription_id" { type = string }
variable "location" {
  type    = string
  default = "westus2"
}
variable "image" { type = string }
variable "public" {
  type    = bool
  default = false
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-policy-foundry"
  location = var.location
}

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-policy-foundry"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "env" {
  name                       = "cae-policy-foundry"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
}

resource "random_password" "api_token" {
  length  = 40
  special = false
}

resource "azurerm_container_app" "foundry" {
  name                         = "policy-foundry"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"

  secret {
    name  = "api-token"
    value = random_password.api_token.result
  }

  template {
    min_replicas = 0
    max_replicas = 2
    container {
      name   = "foundry"
      image  = var.image
      cpu    = 0.5
      memory = "1Gi"
      env {
        name        = "FOUNDRY_API_TOKEN"
        secret_name = "api-token"
      }
      liveness_probe {
        transport = "HTTP"
        port      = 8000
        path      = "/healthz"
      }
    }
  }

  ingress {
    external_enabled = var.public
    target_port      = 8000
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

output "url" { value = "https://${azurerm_container_app.foundry.ingress[0].fqdn}" }
output "api_token" {
  value     = random_password.api_token.result
  sensitive = true
}
