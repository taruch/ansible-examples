# f5_demo_aws_provision

Provisions F5 BIG-IP VE in AWS for demo purposes. Creates all necessary networking
infrastructure (VPC, subnet, IGW, security group) and launches a BIG-IP VE instance.

## What it does

1. Finds the latest F5 BIG-IP VE AMI (PAYG 1Gbps) if not explicitly provided
2. Creates VPC and public subnet (or uses existing if provided)
3. Creates internet gateway and route table
4. Creates security group (SSH:22, HTTPS:443, management:8443)
5. Launches F5 BIG-IP VE EC2 instance
6. Waits for BIG-IP to initialize (mcpd ready)
7. Creates Cloudflare A record pointing to BIG-IP public IP
8. Saves instance details to `inventory/demo_bigip.yml`

## Requirements

- **AWS credentials** configured (env vars, `~/.aws/credentials`, or IAM role)
- **F5 BIG-IP VE subscription** in AWS Marketplace (or use BYOL AMI)
- **SSH key pair** in AWS for initial access
- **`amazon.aws` collection** (>= 9.0.0)
- **`community.general` collection** (for Cloudflare DNS)

## Role Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `aws_region` | Yes | `us-east-1` | AWS region |
| `aws_key_name` | Yes | - | SSH key pair name |
| `f5_admin_password` | Yes | - | BIG-IP admin password |
| `cloudflare_zone` | Yes | - | Cloudflare DNS zone |
| `cloudflare_api_token` | Yes | - | Cloudflare API token |
| `cert_fqdn` | No | `bigip-demo.{{ cloudflare_zone }}` | FQDN for cert/DNS |
| `f5_instance_type` | No | `t3.xlarge` | EC2 instance type |
| `f5_ami_id` | No | (auto-detected) | F5 BIG-IP VE AMI ID |
| `vpc_id` | No | (created) | Existing VPC ID |
| `subnet_id` | No | (created) | Existing subnet ID |
| `demo_tag` | No | `f5-cert-demo` | Tag for all resources |

## Instance Sizing

F5 BIG-IP VE requires **minimum 2 vCPU and 8GB RAM**:

- **t3.xlarge** (4 vCPU, 16GB) - Minimum for demo, ~$0.17/hr
- **t3.2xlarge** (8 vCPU, 32GB) - Better performance, ~$0.33/hr
- **m5.xlarge** (4 vCPU, 16GB) - Production-ready, ~$0.19/hr

## AMI Selection

The role auto-detects the latest F5 BIG-IP VE PAYG (Best 1Gbps) AMI. To use a
specific AMI or BYOL license:

```yaml
f5_ami_id: ami-0123456789abcdef0
```

Find AMIs:
```bash
aws ec2 describe-images \
  --owners 679593333241 \
  --filters "Name=name,Values=F5 BIGIP-16* PAYG*" \
  --query 'Images[*].[ImageId,Name,CreationDate]' \
  --output table
```

## Example Playbook

```yaml
- hosts: localhost
  roles:
    - role: f5_demo_aws_provision
      vars:
        aws_region: us-east-1
        aws_key_name: my-keypair
        f5_admin_password: StrongPassword123!
        cloudflare_zone: example.com
        cloudflare_api_token: "{{ lookup('env', 'CLOUDFLARE_API_TOKEN') }}"
```

## Outputs

The role sets the following facts:

- `bigip_instance_id` - EC2 instance ID
- `bigip_mgmt_ip` - BIG-IP management IP (public)
- `bigip_public_ip` - BIG-IP public IP
- `bigip_private_ip` - BIG-IP private IP

And creates `inventory/demo_bigip.yml` with the instance details.

## Cleanup

Use the `demo_teardown.yml` playbook to remove all resources:

```bash
ansible-playbook demo_teardown.yml \
  -e aws_region=us-east-1 \
  -e cloudflare_zone=example.com \
  -e demo_tag=f5-cert-demo
```

## Cost Estimate

Running for 8 hours (typical demo):
- **EC2 instance (t3.xlarge):** ~$1.36
- **EBS storage (80GB):** ~$0.07
- **Data transfer:** Negligible for demo traffic
- **Total:** ~$1.50 per demo session

**Don't forget to tear down** when done to avoid ongoing charges!

## Troubleshooting

**BIG-IP not ready after 15 minutes:**

Check the instance's system log in AWS console. BIG-IP VE can take 10-15 minutes
to fully initialize on first boot.

**AMI not found:**

The F5 BIG-IP VE AMI filter may need adjustment for newer versions. Check AWS
Marketplace or use an explicit AMI ID.

**Security group issues:**

Verify your AWS account limits allow creating security groups. Check VPC limits
in the AWS console.

## License

MIT

## Author

Todd Ruch
