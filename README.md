## Overview

This project implements a cloud cost hygiene foundation for NimbusKart,
an e-commerce startup whose monthly AWS bill grew from ~$400 to ~$2,100
due to orphaned and untagged resources.

Part A provisions NimbusKart's staging infrastructure (VPC, EC2, S3, EBS)
using Terraform against LocalStack — no real AWS account needed. Part B
introduces the "Cost Janitor", a Python + boto3 automation script that scans
for orphaned resources (unattached EBS volumes, stopped EC2 instances,
unassociated Elastic IPs, and untagged resources) and produces a structured
report. Part C outlines how this foundation would be hardened and scaled for
a real multi-cloud production environment. The entire pipeline is wired into
GitHub Actions — on every PR, the janitor runs automatically and posts a
cost report as a PR comment.

## How to run locally

```bash
# 1. Clone the repo
git clone https://github.com/Kavyachandrasekar/nimbuskart-cost-hygiene.git
cd nimbuskart-cost-hygiene

# 2. Start LocalStack
docker run --rm -d -p 4566:4566 --name localstack localstack/localstack:3.0

# 3. Install tflocal
pip install terraform-local

# 4. Apply Terraform (creates infra on LocalStack)
cd terraform
tflocal init
tflocal apply -auto-approve
cd ..

# 5. Install janitor dependencies
cd janitor
pip install -r requirements.txt

# 6. Run Cost Janitor (dry-run)
python janitor.py --dry-run

# 7. View reports
cat report.json
cat summary.md

# 8. Run in delete mode (removes orphans, skips Protected=true)
python janitor.py --delete

# 9. Run unit tests
python -m pytest tests/ -v
```


## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    GitHub Actions                    │
│  PR opened → LocalStack → Terraform → Cost Janitor  │
│                    ↓                                 │
│           PR Comment (report posted)                 │
└─────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────┐
│                    LocalStack                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │   VPC    │  │  2x EC2  │  │   S3 (app-logs)  │  │
│  │10.20.0/16│  │ t3.micro │  │   versioning on  │  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
│  ┌──────────┐  ┌──────────┐                         │
│  │  2x      │  │   EBS    │                         │
│  │ Subnets  │  │ (orphan) │                         │
│  └──────────┘  └──────────┘                         │
└─────────────────────────────────────────────────────┘
          ↓
┌─────────────────────────────────────────────────────┐
│                   Cost Janitor                       │
│  scan_ebs() → scan_ec2() → scan_eips() → scan_tags()│
│                    ↓                                 │
│          report.json + summary.md                    │
└─────────────────────────────────────────────────────┘
```


## Decisions & deviations

- **SSH CIDR defaulted to 0.0.0.0/0** — Spec required it but flagged as unsafe.
  In production, this should be restricted to a specific bastion or VPN CIDR.

- **S3 Lifecycle configuration removed** — LocalStack + Terraform AWS Provider v5
  causes a timeout waiting for lifecycle state stabilization. This is a LocalStack
  limitation, not a code issue. Works correctly on real AWS.

- **Single network module** — Spec asked for at least one reusable module.
  Extracted network (VPC + subnets) as a module; remaining resources stay in
  root main.tf for simplicity.

- **ami-12345678 placeholder** — LocalStack does not validate AMI IDs, so a
  dummy AMI is used. Real deployment would use a valid AMI via data source.

- **EC2 root volumes flagged for missing tags** — Root EBS volumes are
  automatically created by AWS/LocalStack when EC2 instances launch. These
  volumes inherit no tags by default, so the janitor correctly flags them.
  This is expected behaviour, not a bug.



## Trade-offs

- **LocalStack over real AWS** — Keeps the assignment free and reproducible,
  but LocalStack does not fully support all AWS APIs (e.g. S3 lifecycle rules).
  With one more week, I would test against a real AWS account using IAM sandbox.

- **Single region/account** — The janitor scans one region and one account only.
  With more time, I would add multi-account support using AWS Organizations and
  assumed IAM roles.

- **No persistent cost history** — Each scan produces a fresh report with no
  historical trending. With more time, I would store results in DynamoDB or S3
  and build a simple trend dashboard.

- **No notifications** — Orphans are reported via PR comment only. With more
  time, I would add Slack and email alerts via SNS.

- **Static cost estimates** — Pricing is hard-coded in constants.py. With more
  time, I would pull live pricing from the AWS Pricing API.


## AI usage disclosure

**Tools used:** Claude (Anthropic) and ChatGPT (OpenAI).

- Claude was used for guidance throughout Parts A, B, and C — explaining
  concepts (boto3, argparse, GitHub Actions), reviewing code structure,
  and helping debug issues like the S3 lifecycle timeout and the GitHub
  Actions PR comment permission error.

- ChatGPT was used during initial Part A Terraform setup for boilerplate
  structure and module layout.

**One thing AI got wrong:** Claude initially suggested a 10-minute timeout
for the S3 lifecycle configuration to fix the LocalStack compatibility issue.
This did not work — the root cause was a LocalStack API limitation, not a
timeout problem. I identified this by reading the LocalStack docs and removed
the resource entirely with proper documentation.

**One section written without AI help:** The "Decisions & deviations" section
was written manually — I wanted to document my own judgment calls and
trade-offs in my own words, since that section reflects my actual
decision-making process during the assignment.
