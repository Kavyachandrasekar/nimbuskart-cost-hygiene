# Cost Janitor Report

**Scan time:** 2026-05-23T19:22:00Z
**Account:** 000000000000 | **Region:** us-east-1

## Summary
| Metric | Value |
|--------|-------|
| Total orphans found | 3 |
| Estimated monthly waste | $0.64 |

## Findings

| Resource ID | Type | Reason | Age (days) | Est. Cost/month |
|-------------|------|--------|-----------|-----------------|
| vol-0a912d93 | ebs_volume | unattached | 0 | $0.64 |
| vol-c86fac06 | ebs_volume | missing_tags:Project,Environment,Owner | 0 | $0.0 |
| vol-c24f046d | ebs_volume | missing_tags:Project,Environment,Owner | 0 | $0.0 |