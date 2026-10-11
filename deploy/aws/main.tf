# AWS ECS Fargate behind an Application Load Balancer. `terraform validate`-checked; review before apply.
#   terraform init && terraform apply -var vpc_id=... -var 'public_subnet_ids=[...]' -var 'private_subnet_ids=[...]' -var image=...
# For the governed production design (Devin over PrivateLink), see infra/privatelink.
terraform {
  required_version = ">= 1.6"
  required_providers {
    aws    = { source = "hashicorp/aws", version = ">= 6.0" }
    random = { source = "hashicorp/random", version = ">= 3.6" }
  }
}

variable "region" {
  type    = string
  default = "us-west-2"
}
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "private_subnet_ids" { type = list(string) }
variable "image" { type = string }
variable "certificate_arn" {
  type        = string
  default     = ""
  description = "ACM certificate for HTTPS. Empty = HTTP listener only (demo)."
}
variable "allowed_cidrs" {
  type        = list(string)
  default     = ["0.0.0.0/0"]
  description = "Who may reach the load balancer. Narrow this for non-public demos."
}

provider "aws" { region = var.region }

resource "random_password" "api_token" {
  length  = 40
  special = false
}

resource "aws_secretsmanager_secret" "api_token" { name_prefix = "policy-foundry-api-token-" }

resource "aws_secretsmanager_secret_version" "api_token" {
  secret_id     = aws_secretsmanager_secret.api_token.id
  secret_string = random_password.api_token.result
}

resource "aws_ecr_repository" "foundry" {
  name                 = "aigovops-policy-foundry"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_cloudwatch_log_group" "foundry" {
  name              = "/ecs/policy-foundry"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "foundry" {
  name = "policy-foundry"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "exec" {
  name_prefix        = "foundry-exec-"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy_attachment" "exec" {
  role       = aws_iam_role.exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "exec_secret" {
  role = aws_iam_role.exec.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.api_token.arn }]
  })
}

resource "aws_ecs_task_definition" "foundry" {
  family                   = "policy-foundry"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.exec.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }
  container_definitions = jsonencode([{
    name                   = "foundry"
    image                  = var.image
    essential              = true
    readonlyRootFilesystem = true
    portMappings           = [{ containerPort = 8000, protocol = "tcp" }]
    secrets                = [{ name = "FOUNDRY_API_TOKEN", valueFrom = aws_secretsmanager_secret.api_token.arn }]
    mountPoints            = [{ sourceVolume = "tmp", containerPath = "/tmp" }]
    logConfiguration = {
      logDriver = "awslogs"
      options   = { awslogs-group = aws_cloudwatch_log_group.foundry.name, awslogs-region = var.region, awslogs-stream-prefix = "foundry" }
    }
  }])
  volume { name = "tmp" }
}

resource "aws_security_group" "alb" {
  name_prefix = "foundry-alb-"
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "alb_in" {
  for_each          = toset(var.allowed_cidrs)
  security_group_id = aws_security_group.alb.id
  ip_protocol       = "tcp"
  from_port         = var.certificate_arn == "" ? 80 : 443
  to_port           = var.certificate_arn == "" ? 80 : 443
  cidr_ipv4         = each.value
}

resource "aws_vpc_security_group_egress_rule" "alb_out" {
  security_group_id            = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.task.id
}

resource "aws_security_group" "task" {
  name_prefix = "foundry-task-"
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "task_in" {
  security_group_id            = aws_security_group.task.id
  ip_protocol                  = "tcp"
  from_port                    = 8000
  to_port                      = 8000
  referenced_security_group_id = aws_security_group.alb.id
}

resource "aws_vpc_security_group_egress_rule" "task_out" {
  security_group_id = aws_security_group.task.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0" # ECR, Secrets Manager, CloudWatch (use VPC endpoints to remove)
}

resource "aws_lb" "foundry" {
  name                       = "policy-foundry"
  load_balancer_type         = "application"
  subnets                    = var.public_subnet_ids
  security_groups            = [aws_security_group.alb.id]
  drop_invalid_header_fields = true
}

resource "aws_lb_target_group" "foundry" {
  name        = "policy-foundry"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check { path = "/healthz" }
}

resource "aws_lb_listener" "http" {
  count             = var.certificate_arn == "" ? 1 : 0
  load_balancer_arn = aws_lb.foundry.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.foundry.arn
  }
}

resource "aws_lb_listener" "https" {
  count             = var.certificate_arn == "" ? 0 : 1
  load_balancer_arn = aws_lb.foundry.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.foundry.arn
  }
}

resource "aws_ecs_service" "foundry" {
  name            = "policy-foundry"
  cluster         = aws_ecs_cluster.foundry.id
  task_definition = aws_ecs_task_definition.foundry.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.foundry.arn
    container_name   = "foundry"
    container_port   = 8000
  }
  depends_on = [aws_lb_listener.http, aws_lb_listener.https]
}

output "url" { value = "${var.certificate_arn == "" ? "http" : "https"}://${aws_lb.foundry.dns_name}" }
output "ecr_repository" { value = aws_ecr_repository.foundry.repository_url }
output "api_token_secret_arn" { value = aws_secretsmanager_secret.api_token.arn }
