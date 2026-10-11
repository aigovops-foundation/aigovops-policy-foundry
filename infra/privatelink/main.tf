# Governed Policy Foundry -- AWS PrivateLink conduits (reference; `terraform validate` clean, not applied)
#
# Direction matters. In Devin's Customer Dedicated Deployment the CUSTOMER is the PrivateLink
# service PROVIDER (NLB + VPC Endpoint Service per internal domain) and COGNITION is the CONSUMER
# (it creates Interface VPC Endpoints in the dedicated tenant VPC and sends a connection request).
# Every NLB here targets the Beacon policy enforcement point (PEP), never the backend directly,
# so each Devin request into the company crosses the gate and is receipted.
#
# Separately, the governance VPC consumes AWS services (Bedrock, KMS, Secrets Manager, STS, Logs,
# S3) through interface/gateway endpoints, and reaches api.devin.ai only through an
# allowlisted egress path (Network Firewall domain list).

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = ">= 6.0" }
  }
}

provider "aws" {
  region = var.region
}

# ------------------------------------------------------------------ variables

variable "region" {
  type    = string
  default = "us-west-2"
}

variable "vpc_id" {
  type        = string
  description = "Governance/dev-tools VPC that hosts the Beacon PEP fleet (IT zone, never OT)."
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "At least two private subnets in different AZs."
  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "Use at least two AZs for the NLBs and endpoints."
  }
}

variable "cognition_account_id" {
  type        = string
  description = "Cognition's AWS account ID, supplied by Cognition for the allowed-principal grant."
}

variable "cognition_tenant_region" {
  type        = string
  description = "Region of the Devin dedicated tenant (for cross-region endpoint-service support)."
}

variable "pep_target_ips" {
  type        = list(string)
  description = "Private IPs of the Beacon PEP (Envoy + ext_authz -> Beacon/OPA gate) instances."
}

variable "conduits" {
  description = "One endpoint service per internal domain Devin may reach (Devin docs: per-domain)."
  type = map(object({
    domain = string
    port   = number
  }))
  default = {
    ghes        = { domain = "git.acme-mfg.internal", port = 443 }
    artifactory = { domain = "artifacts.acme-mfg.internal", port = 443 }
    beacon      = { domain = "beacon.acme-mfg.internal", port = 443 } # receipt status + MCP self-check
  }
}

variable "devin_api_allowed_domains" {
  type    = list(string)
  default = [".devin.ai"] # manager -> api.devin.ai control-plane calls
}

variable "flow_log_bucket_arn" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = { system = "governed-policy-foundry", zone = "it-l4", owner = "ai-governance" }
}

# ------------------------------------------------- provider side: Devin -> company

resource "aws_security_group" "nlb" {
  name        = "foundry-devin-conduit-nlb"
  description = "PrivateLink ingress from the Devin dedicated tenant only"
  vpc_id      = var.vpc_id
  tags        = var.tags
}

resource "aws_vpc_security_group_ingress_rule" "nlb_in" {
  for_each          = var.conduits
  security_group_id = aws_security_group.nlb.id
  description       = "PrivateLink traffic for ${each.key}"
  ip_protocol       = "tcp"
  from_port         = each.value.port
  to_port           = each.value.port
  cidr_ipv4         = "0.0.0.0/0" # PrivateLink source IPs are NLB-private; tighten with inbound-rule enforcement below
}

resource "aws_vpc_security_group_egress_rule" "nlb_to_pep" {
  for_each          = toset(var.pep_target_ips)
  security_group_id = aws_security_group.nlb.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "${each.value}/32"
}

resource "aws_lb" "conduit" {
  for_each                         = var.conduits
  name                             = substr("foundry-${each.key}-nlb", 0, 32)
  load_balancer_type               = "network"
  internal                         = true
  subnets                          = var.private_subnet_ids
  security_groups                  = [aws_security_group.nlb.id]
  enable_cross_zone_load_balancing = true
  enable_deletion_protection       = true

  enforce_security_group_inbound_rules_on_private_link_traffic = "on"

  tags = merge(var.tags, { conduit = each.key })
}

resource "aws_lb_target_group" "pep" {
  for_each    = var.conduits
  name        = substr("foundry-${each.key}-pep", 0, 32)
  port        = 443
  protocol    = "TCP" # TLS passthrough; the PEP terminates TLS with the internal CA
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    protocol = "HTTPS"
    path     = "/healthz"
    port     = "8443"
  }
  tags = var.tags
}

locals {
  pep_attachments = {
    for pair in setproduct(keys(var.conduits), var.pep_target_ips) :
    "${pair[0]}-${pair[1]}" => { conduit = pair[0], ip = pair[1] }
  }
}

resource "aws_lb_target_group_attachment" "pep" {
  for_each         = local.pep_attachments
  target_group_arn = aws_lb_target_group.pep[each.value.conduit].arn
  target_id        = each.value.ip
  port             = 443
}

resource "aws_lb_listener" "conduit" {
  for_each          = var.conduits
  load_balancer_arn = aws_lb.conduit[each.key].arn
  port              = each.value.port
  protocol          = "TCP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.pep[each.key].arn
  }
}

resource "aws_vpc_endpoint_service" "conduit" {
  for_each                   = var.conduits
  acceptance_required        = true # every Cognition connection request is accepted by a human, and receipted
  network_load_balancer_arns = [aws_lb.conduit[each.key].arn]
  allowed_principals         = ["arn:aws:iam::${var.cognition_account_id}:root"]
  supported_regions          = distinct([var.region, var.cognition_tenant_region])
  supported_ip_address_types = ["ipv4"]
  tags                       = merge(var.tags, { conduit = each.key, domain = each.value.domain })
}

# ------------------------------------------- consumer side: governance VPC -> AWS services

resource "aws_security_group" "endpoints" {
  name        = "foundry-aws-endpoints"
  description = "HTTPS from the governance VPC to AWS interface endpoints"
  vpc_id      = var.vpc_id
  tags        = var.tags
}

data "aws_vpc" "this" {
  id = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "endpoints_in" {
  security_group_id = aws_security_group.endpoints.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = data.aws_vpc.this.cidr_block
}

resource "aws_vpc_endpoint" "aws_services" {
  for_each            = toset(["bedrock-runtime", "kms", "secretsmanager", "sts", "logs", "states"])
  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.private_subnet_ids
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true
  tags                = merge(var.tags, { endpoint = each.key })
}

data "aws_route_tables" "private" {
  vpc_id = var.vpc_id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = data.aws_route_tables.private.ids
  tags              = var.tags
}

# ------------------------------------------------- egress allowlist: manager -> api.devin.ai

resource "aws_networkfirewall_rule_group" "devin_api_allowlist" {
  name     = "foundry-devin-api-allowlist"
  type     = "STATEFUL"
  capacity = 100
  rule_group {
    rules_source {
      rules_source_list {
        generated_rules_type = "ALLOWLIST"
        target_types         = ["TLS_SNI", "HTTP_HOST"]
        targets              = var.devin_api_allowed_domains
      }
    }
  }
  tags = var.tags
}

# ------------------------------------------------------------------ evidence

resource "aws_flow_log" "vpc" {
  vpc_id               = var.vpc_id
  traffic_type         = "ALL"
  log_destination_type = "s3"
  log_destination      = var.flow_log_bucket_arn
  tags                 = var.tags
}

# ------------------------------------------------------------------ outputs

output "endpoint_service_names" {
  description = "Send these to Cognition with the ports and domains (Devin private-networking runbook)."
  value       = { for k, v in aws_vpc_endpoint_service.conduit : k => v.service_name }
}

output "domains_and_ports" {
  value = { for k, v in var.conduits : k => "${v.domain}:${v.port}" }
}
