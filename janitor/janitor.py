"""
Cost Janitor — AWS orphan resource scanner for NimbusKart
Usage:
    python janitor.py            # dry-run by default
    python janitor.py --dry-run  # explicit dry-run
    python janitor.py --delete   # actually delete orphans (skips Protected=true)
"""

import boto3
import json
import argparse
import sys
from datetime import datetime, timezone
from constants import (
    EBS_GP3_COST_PER_GB_MONTH,
    EIP_MONTHLY_COST,
    EC2_STOPPED_MONTHLY_COST,
    DEFAULT_STOPPED_DAYS_THRESHOLD,
)

REQUIRED_TAGS = ["Project", "Environment", "Owner"]


# ─────────────────────────────────────────────
# 1. ARGUMENT PARSING
# ─────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(description="Cost Janitor - AWS orphan resource scanner")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", default=True)
    group.add_argument("--delete", action="store_true")
    parser.add_argument("--stopped-days", type=int, default=DEFAULT_STOPPED_DAYS_THRESHOLD)
    return parser.parse_args()


# ─────────────────────────────────────────────
# 2. boto3 CLIENT SETUP
# ─────────────────────────────────────────────
def get_clients():
    session = boto3.Session(
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )
    endpoint = "http://localhost:4566"
    return {
        "ec2": session.client("ec2", endpoint_url=endpoint),
        "sts": session.client("sts", endpoint_url=endpoint),
    }


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def tags_to_dict(tag_list):
    if not tag_list:
        return {}
    return {tag["Key"]: tag["Value"] for tag in tag_list}

def is_protected(tags_dict):
    return tags_dict.get("Protected", "").lower() == "true"

def missing_tags(tags_dict):
    return [tag for tag in REQUIRED_TAGS if not tags_dict.get(tag)]


# ─────────────────────────────────────────────
# 3. SCAN FUNCTIONS
# ─────────────────────────────────────────────
def scan_unattached_ebs(ec2_client):
    findings = []
    response = ec2_client.describe_volumes(
        Filters=[{"Name": "status", "Values": ["available"]}]
    )
    for volume in response["Volumes"]:
        vol_id    = volume["VolumeId"]
        size_gb   = volume["Size"]
        tags_dict = tags_to_dict(volume.get("Tags", []))
        create_time = volume["CreateTime"]
        age_days = (datetime.now(timezone.utc) - create_time).days
        monthly_cost = round(size_gb * EBS_GP3_COST_PER_GB_MONTH, 2)
        findings.append({
            "resource_id":                vol_id,
            "resource_type":              "ebs_volume",
            "reason":                     "unattached",
            "age_days":                   age_days,
            "estimated_monthly_cost_usd": monthly_cost,
            "tags":                       {t: tags_dict.get(t) for t in REQUIRED_TAGS},
            "suggested_action":           "delete",
            "safe_to_auto_delete":        not is_protected(tags_dict) and len(missing_tags(tags_dict)) == 0,
            "_raw_tags":                  tags_dict,
        })
    return findings


def scan_stopped_ec2(ec2_client, stopped_days_threshold):
    findings = []
    response = ec2_client.describe_instances(
        Filters=[{"Name": "instance-state-name", "Values": ["stopped"]}]
    )
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]
            tags_dict   = tags_to_dict(instance.get("Tags", []))
            reason      = instance.get("StateTransitionReason", "")
            age_days    = 0
            try:
                date_str     = reason.split("(")[-1].replace(" GMT)", "").strip()
                stopped_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                age_days     = (datetime.now(timezone.utc) - stopped_time).days
            except Exception:
                age_days = 0
            if age_days >= stopped_days_threshold:
                findings.append({
                    "resource_id":                instance_id,
                    "resource_type":              "ec2_instance",
                    "reason":                     f"stopped_over_{stopped_days_threshold}_days",
                    "age_days":                   age_days,
                    "estimated_monthly_cost_usd": EC2_STOPPED_MONTHLY_COST,
                    "tags":                       {t: tags_dict.get(t) for t in REQUIRED_TAGS},
                    "suggested_action":           "review_and_terminate",
                    "safe_to_auto_delete":        False,
                    "_raw_tags":                  tags_dict,
                })
    return findings


def scan_unattached_eips(ec2_client):
    findings = []
    response = ec2_client.describe_addresses()
    for address in response["Addresses"]:
        if "InstanceId" not in address:
            allocation_id = address.get("AllocationId", address.get("PublicIp"))
            tags_dict     = tags_to_dict(address.get("Tags", []))
            findings.append({
                "resource_id":                allocation_id,
                "resource_type":              "elastic_ip",
                "reason":                     "unassociated",
                "age_days":                   0,
                "estimated_monthly_cost_usd": EIP_MONTHLY_COST,
                "tags":                       {t: tags_dict.get(t) for t in REQUIRED_TAGS},
                "suggested_action":           "release",
                "safe_to_auto_delete":        not is_protected(tags_dict),
                "_raw_tags":                  tags_dict,
            })
    return findings


def scan_missing_tags(ec2_client):
    findings = []
    # EC2 instances
    response = ec2_client.describe_instances()
    for reservation in response["Reservations"]:
        for instance in reservation["Instances"]:
            if instance["State"]["Name"] == "terminated":
                continue
            instance_id = instance["InstanceId"]
            tags_dict   = tags_to_dict(instance.get("Tags", []))
            absent      = missing_tags(tags_dict)
            if absent:
                findings.append({
                    "resource_id":                instance_id,
                    "resource_type":              "ec2_instance",
                    "reason":                     f"missing_tags:{','.join(absent)}",
                    "age_days":                   0,
                    "estimated_monthly_cost_usd": 0.0,
                    "tags":                       {t: tags_dict.get(t) for t in REQUIRED_TAGS},
                    "suggested_action":           "add_missing_tags",
                    "safe_to_auto_delete":        False,
                    "_raw_tags":                  tags_dict,
                })
    # EBS volumes
    response = ec2_client.describe_volumes()
    for volume in response["Volumes"]:
        vol_id    = volume["VolumeId"]
        tags_dict = tags_to_dict(volume.get("Tags", []))
        absent    = missing_tags(tags_dict)
        if absent:
            findings.append({
                "resource_id":                vol_id,
                "resource_type":              "ebs_volume",
                "reason":                     f"missing_tags:{','.join(absent)}",
                "age_days":                   0,
                "estimated_monthly_cost_usd": 0.0,
                "tags":                       {t: tags_dict.get(t) for t in REQUIRED_TAGS},
                "suggested_action":           "add_missing_tags",
                "safe_to_auto_delete":        False,
                "_raw_tags":                  tags_dict,
            })
    return findings


# ─────────────────────────────────────────────
# 4. DELETE FUNCTION
# ─────────────────────────────────────────────
def delete_resource(ec2_client, finding):
    tags_dict     = finding.get("_raw_tags", {})
    if is_protected(tags_dict):
        print(f"  [SKIP] {finding['resource_id']} is Protected=true — skipping.")
        return
    resource_type = finding["resource_type"]
    resource_id   = finding["resource_id"]
    try:
        if resource_type == "ebs_volume" and finding["reason"] == "unattached":
            ec2_client.delete_volume(VolumeId=resource_id)
            print(f"  [DELETED] EBS volume {resource_id}")
        elif resource_type == "elastic_ip" and finding["reason"] == "unassociated":
            ec2_client.release_address(AllocationId=resource_id)
            print(f"  [RELEASED] Elastic IP {resource_id}")
        else:
            print(f"  [SKIP] {resource_id} ({resource_type}) requires human review.")
    except Exception as e:
        print(f"  [ERROR] Failed to delete {resource_id}: {e}")


# ─────────────────────────────────────────────
# 5. REPORT BUILDER
# ─────────────────────────────────────────────
def build_report(findings, account_id, region="us-east-1"):
    total_waste    = round(sum(f["estimated_monthly_cost_usd"] for f in findings), 2)
    clean_findings = [{k: v for k, v in f.items() if not k.startswith("_")} for f in findings]
    return {
        "scan_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "account_id":     account_id,
        "region":         region,
        "summary": {
            "total_orphans":               len(findings),
            "estimated_monthly_waste_usd": total_waste,
        },
        "findings": clean_findings,
    }

def write_report_json(report, path="report.json"):
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n[✓] report.json written → {path}")

def write_markdown_summary(report, path="summary.md"):
    lines = []
    lines.append("# Cost Janitor Report\n")
    lines.append(f"**Scan time:** {report['scan_timestamp']}")
    lines.append(f"**Account:** {report['account_id']} | **Region:** {report['region']}\n")
    lines.append("## Summary")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total orphans found | {report['summary']['total_orphans']} |")
    lines.append(f"| Estimated monthly waste | ${report['summary']['estimated_monthly_waste_usd']} |")
    lines.append("")
    if report["findings"]:
        lines.append("## Findings\n")
        lines.append("| Resource ID | Type | Reason | Age (days) | Est. Cost/month |")
        lines.append("|-------------|------|--------|-----------|-----------------|")
        for f in report["findings"]:
            lines.append(
                f"| {f['resource_id']} | {f['resource_type']} | {f['reason']} "
                f"| {f['age_days']} | ${f['estimated_monthly_cost_usd']} |"
            )
    else:
        lines.append("## ✅ No orphans found! Cloud is clean.")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"[✓] summary.md written → {path}")


# ─────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────
def main():
    args       = parse_args()
    delete_mode = args.delete
    mode_label  = "DELETE" if delete_mode else "DRY-RUN"
    print(f"\n{'='*50}")
    print(f"  Cost Janitor — Mode: {mode_label}")
    print(f"{'='*50}\n")

    clients    = get_clients()
    ec2        = clients["ec2"]
    sts        = clients["sts"]

    try:
        account_id = sts.get_caller_identity()["Account"]
    except Exception:
        account_id = "000000000000"

    print("[1/4] Scanning unattached EBS volumes...")
    ebs_findings = scan_unattached_ebs(ec2)
    print(f"      → {len(ebs_findings)} found")

    print("[2/4] Scanning stopped EC2 instances...")
    ec2_findings = scan_stopped_ec2(ec2, args.stopped_days)
    print(f"      → {len(ec2_findings)} found")

    print("[3/4] Scanning unattached Elastic IPs...")
    eip_findings = scan_unattached_eips(ec2)
    print(f"      → {len(eip_findings)} found")

    print("[4/4] Scanning resources with missing tags...")
    tag_findings = scan_missing_tags(ec2)
    print(f"      → {len(tag_findings)} found")

    all_findings = ebs_findings + ec2_findings + eip_findings + tag_findings

    if delete_mode and all_findings:
        print(f"\n[DELETE MODE] Attempting to clean up {len(all_findings)} orphans...")
        for finding in all_findings:
            delete_resource(ec2, finding)

    report = build_report(all_findings, account_id)
    write_report_json(report)
    write_markdown_summary(report)

    print(f"\n{'='*50}")
    print(f"  Total orphans : {report['summary']['total_orphans']}")
    print(f"  Monthly waste : ${report['summary']['estimated_monthly_waste_usd']}")
    print(f"{'='*50}")

    if not delete_mode and all_findings:
        print("\n[!] Orphans found in dry-run mode → exiting with code 1 (CI will flag this)")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
