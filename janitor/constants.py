# Pricing constants for AWS resource cost estimation
# Source: https://aws.amazon.com/ebs/pricing/ (us-east-1, verified May 2026)
EBS_GP2_COST_PER_GB_MONTH = 0.10
EBS_GP3_COST_PER_GB_MONTH = 0.08

# Source: https://aws.amazon.com/ec2/pricing/on-demand/ (us-east-1)
EC2_T3_MICRO_COST_PER_HOUR = 0.0104
EC2_HOURS_PER_MONTH = 730

# Source: https://aws.amazon.com/ec2/pricing/on-demand/ (Elastic IP)
EIP_COST_PER_HOUR_UNATTACHED = 0.005
EIP_MONTHLY_COST = round(EIP_COST_PER_HOUR_UNATTACHED * EC2_HOURS_PER_MONTH, 2)

EC2_STOPPED_MONTHLY_COST = 0.0
DEFAULT_STOPPED_DAYS_THRESHOLD = 14
