# Design Note — Cost Janitor

## Multi-cloud Reality

Core logic (report schema, exit codes) stays unchanged in `core.py`.
Each cloud gets its own provider module:

janitor/
├── core.py         ← common logic
├── providers/
│   ├── base.py     ← BaseScanner (interface)
│   ├── aws.py      ← boto3
│   ├── gcp.py      ← google-cloud-sdk (future)
│   └── azure.py    ← azure-sdk (future)

GCP: EBS→Persistent Disk, EC2→Compute Engine, EIP→Static IP.
Adding GCP = write `gcp.py` only. Core untouched.

## Permissions

Read-only policy for dry-run:

{
  "Effect": "Allow",
  "Action": [
    "ec2:DescribeVolumes",
    "ec2:DescribeInstances",
    "ec2:DescribeAddresses",
    "sts:GetCallerIdentity"
  ],
  "Resource": "*"
}

Delete mode adds: ec2:DeleteVolume, ec2:ReleaseAddress, ec2:TerminateInstances.

## Safety Net

**1. Volume deleted mid-deployment:**
EBS briefly shows "available" during rolling deploy → janitor deletes it → data loss.
Fix: Only flag volumes unattached > 1 hour. Use Protected=true during deploys.

**2. Stopped EC2 = developer environment:**
Developer stopped instance intentionally → auto-delete destroys their work.
Fix: Never auto-terminate EC2. Always require human approval.

## Observability

| Metric | Threshold |
|--------|-----------|
| orphans.total | > 10 → Slack |
| waste.monthly_usd | > $100 → PagerDuty |
| scan.duration_seconds | > 5 min → alert |
| deletions.count | > 5/run → audit |
| errors.count | Any → immediate alert |

Published to AWS CloudWatch.

## What I Did Not Build

Multi-account scanning, Slack notifications, cost trend tracking over time,
GCP/Azure implementations, and automated EC2 termination — all intentionally
left out due to time constraints and risk.
