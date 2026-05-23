variable "aws_region" {
  description = "AWS region for LocalStack"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "staging"
}

variable "project" {
  description = "Project name"
  type        = string
  default     = "NimbusKart"
}

variable "owner" {
  description = "Resource owner"
  type        = string
  default     = "Chandu"
}

variable "ssh_cidr" {
  description = "CIDR allowed for SSH access"
  type        = string
  default     = "0.0.0.0/0"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_1_cidr" {
  description = "CIDR block for public subnet 1"
  type        = string
  default     = "10.20.1.0/24"
}

variable "public_subnet_2_cidr" {
  description = "CIDR block for public subnet 2"
  type        = string
  default     = "10.20.2.0/24"
}

variable "az_1" {
  description = "Availability zone 1"
  type        = string
  default     = "us-east-1a"
}

variable "az_2" {
  description = "Availability zone 2"
  type        = string
  default     = "us-east-1b"
}
