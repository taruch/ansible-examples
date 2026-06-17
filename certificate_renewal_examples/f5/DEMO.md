# F5 BIG-IP Certificate Renewal Demo

This guide walks you through setting up a demo F5 BIG-IP instance with automated
Let's Encrypt certificate renewal.

## Two Paths Available

### Path A: Automated Provisioning (Recommended)

Use `demo_host_init.yml` to automatically provision F5 BIG-IP VE in AWS with
everything pre-configured. **This is the fastest path** — you'll have a working
demo in ~20 minutes.

**Prerequisites:**
- AWS account with EC2 access
- AWS credentials configured (env vars, `~/.aws/credentials`, or IAM role)
- SSH key pair in AWS
- Cloudflare-managed DNS zone with API token
- Ansible 2.15+ or ansible-navigator with EE support

**Jump to:** [Automated Setup](#automated-setup-path-a)

### Path B: Manual Setup (BYO BIG-IP)

Use your existing F5 BIG-IP instance (physical, VE, cloud) and configure it
manually.

**Prerequisites:**
- F5 BIG-IP instance (physical, VE, or cloud)
- Management IP accessible from your Ansible control node
- Admin credentials
- Cloudflare-managed DNS zone with API token
- Ansible 2.15+ or ansible-navigator with EE support

**Jump to:** [Manual Setup](#manual-setup-path-b)

---

## Automated Setup (Path A)

### Step 1: Prepare AWS credentials

Ensure AWS credentials are configured:

```bash
# Option 1: Environment variables
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_DEFAULT_REGION="us-east-1"

# Option 2: AWS CLI profile
aws configure

# Verify credentials
aws sts get-caller-identity
```

### Step 2: Create secrets file

Create `secrets.yml` (gitignored):

```yaml
---
# Cloudflare
cloudflare_api_token: "YOUR_CLOUDFLARE_API_TOKEN"
cloudflare_zone: example.com

# AWS
aws_region: us-east-1
aws_key_name: my-keypair  # SSH key pair name in AWS

# F5 BIG-IP
f5_admin_password: "StrongPassword123!"

# Optional: customize cert FQDN (defaults to bigip-demo.{{ cloudflare_zone }})
# demo_fqdn: mybigip.example.com
```

```bash
chmod 600 secrets.yml
```

### Step 3: Run the provisioning playbook

```bash
ansible-navigator run demo_host_init.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  --pull-policy missing \
  --mode stdout \
  --pae false \
  -e @secrets.yml
```

**What happens:**
1. Creates VPC, subnet, internet gateway, route table
2. Creates security group (SSH, HTTPS, BIG-IP mgmt)
3. Launches F5 BIG-IP VE EC2 instance (t3.xlarge)
4. Waits for BIG-IP to initialize (~10-15 minutes)
5. Creates Cloudflare A record → BIG-IP public IP
6. Configures BIG-IP (pool, virtual servers, SSL profile)
7. Issues initial Let's Encrypt certificate (staging by default)
8. Imports cert to BIG-IP and configures SSL profile
9. Saves inventory to `inventory/demo_bigip.yml`

**Expected runtime:** ~20 minutes

**Output:**
```
========================================
F5 BIG-IP demo environment is ready!
========================================

BIG-IP Management IP: 3.80.123.45
BIG-IP Public IP:     3.80.123.45
Cert FQDN:            bigip-demo.example.com
Admin username:       admin
Admin password:       StrongPassword123!

Management UI:        https://3.80.123.45:8443
Virtual Server:       https://bigip-demo.example.com

Initial cert issued:  STAGING
```

### Step 4: Verify the demo environment

```bash
# Check HTTPS (will show cert warning for staging cert)
curl -vk https://bigip-demo.example.com

# Login to BIG-IP management UI
# https://3.80.123.45:8443
# Username: admin
# Password: StrongPassword123!
```

### Step 5: Test the renewal flow

The renewal playbook works against the auto-generated inventory:

```bash
ansible-navigator run renew_f5_cert_v2.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  --mode stdout \
  --pae false \
  -i inventory/demo_bigip.yml \
  -e @secrets.yml
```

First run should no-op (cert was just issued). Force a renewal:

```bash
ansible-navigator run renew_f5_cert_v2.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  --mode stdout \
  --pae false \
  -i inventory/demo_bigip.yml \
  -e @secrets.yml \
  -e cert_remaining_days=999
```

### Step 6: Clean up AWS resources

**Important:** Tear down to avoid ongoing charges (~$0.17/hour for t3.xlarge):

```bash
ansible-navigator run demo_teardown.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  --mode stdout \
  --pae false \
  -e @secrets.yml
```

This removes:
- EC2 instance
- VPC and all networking
- Security group
- Cloudflare DNS record
- Local inventory file

**Cost estimate:** ~$1.50 for an 8-hour demo session.

---

## Manual Setup (Path B)

### Prerequisites

1. **F5 BIG-IP instance**
   - BIG-IP VE in AWS/Azure/GCP, or
   - Physical BIG-IP, or
   - BIG-IP running in your lab
   - Management IP accessible from your Ansible control node
   - Admin credentials

2. **Cloudflare-managed DNS zone**
   - A zone you control (e.g., `example.com`)
   - API token with `Zone:Zone:Read` + `Zone:DNS:Edit` permissions

3. **Ansible / ansible-navigator**
   - Ansible 2.15+ or ansible-navigator with EE support
   - Access to the execution environment image (or build it locally)

## Step 1: Prepare your BIG-IP

1. **Create a client-SSL profile** (or use an existing one)

   ```bash
   # SSH to BIG-IP
   ssh admin@<bigip-ip>
   
   # Create a client-SSL profile
   tmsh create ltm profile client-ssl clientssl_demo_example_com \
     defaults-from clientssl
   
   # Save config
   tmsh save sys config
   ```

2. **Create a test virtual server** (optional, for validation)

   ```bash
   tmsh create ltm pool demo_pool members add { 10.0.0.10:80 }
   
   tmsh create ltm virtual demo_vs \
     destination 0.0.0.0:443 \
     ip-protocol tcp \
     pool demo_pool \
     profiles add { clientssl_demo_example_com { context clientside } tcp }
   
   tmsh save sys config
   ```

3. **Note your BIG-IP details:**
   - Management IP: `___________________`
   - Admin username: `admin` (or custom)
   - Admin password: `___________________`
   - Client-SSL profile name: `clientssl_demo_example_com`
   - Partition: `Common` (or custom)

## Step 2: Configure Cloudflare

1. **Create a DNS A record** for your cert FQDN

   - FQDN: `bigip-demo.example.com` (or your choice)
   - Points to: Your BIG-IP's public IP (or private IP if internal-only)
   - TTL: 300 (or Auto)

2. **Generate a Cloudflare API token**

   - Go to https://dash.cloudflare.com/profile/api-tokens
   - Create Token → "Edit zone DNS" template
   - Zone Resources: Include → Specific zone → `example.com`
   - Permissions:
     - `Zone:Zone:Read`
     - `Zone:DNS:Edit`
   - Copy the token (you'll need it in secrets.yml)

## Step 3: Prepare the inventory and secrets

1. **Edit `inventory/hosts.yml`:**

   ```yaml
   ---
   all:
     children:
       bigip:
         hosts:
           bigip-demo.example.com:
             ansible_host: 10.1.1.100  # BIG-IP management IP
             f5_validate_certs: false   # Use true if BIG-IP has valid mgmt cert
             clientssl_profile: clientssl_demo_example_com
             partition: Common
   ```

2. **Create `secrets.yml`** (gitignored):

   ```yaml
   ---
   cloudflare_api_token: "YOUR_CLOUDFLARE_API_TOKEN_HERE"
   f5_user: admin
   f5_password: "YOUR_BIGIP_ADMIN_PASSWORD_HERE"
   ```

   ```bash
   # Mark it as secret
   chmod 600 secrets.yml
   ```

3. **Set your zone:**

   ```bash
   export CLOUDFLARE_ZONE=example.com
   ```

## Step 4: Install collections (if running with system Ansible)

```bash
ansible-galaxy collection install -r requirements.yml
```

Skip this if using ansible-navigator with the pre-built EE image — collections
are already bundled.

## Step 5: Run the initial cert issuance

```bash
# Using ansible-navigator (recommended)
ansible-navigator run renew_f5_cert_v2.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  --pull-policy missing \
  --mode stdout \
  --pae false \
  -i inventory/hosts.yml \
  -e @secrets.yml \
  -e cloudflare_zone=$CLOUDFLARE_ZONE

# OR using system ansible
ansible-playbook -i inventory/hosts.yml renew_f5_cert_v2.yml \
  -e @secrets.yml \
  -e cloudflare_zone=$CLOUDFLARE_ZONE
```

**What happens:**

1. Pre-flight checks the SSL profile — no valid cert found (or cert is expired)
2. Let's Encrypt DNS-01 challenge runs against Cloudflare
3. Cert/key/chain imported to BIG-IP with versioned names
4. Client-SSL profile updated to reference the new cert
5. Config saved

**Expected output (last task):**

```
TASK [f5_tls : Renewal summary] ************************************************
ok: [bigip-demo.example.com] =>
  msg:
  - 'F5 BIG-IP:      10.1.1.100'
  - 'SSL Profile:    clientssl_demo_example_com'
  - 'New cert name:  bigip_demo_example_com_20260602.crt'
  - 'Cert FQDN:      bigip-demo.example.com'
  - 'Backup saved:   /tmp/bigip-demo.example.com_pre_cert_renewal_20260602.ucs'
```

## Step 6: Verify the cert is live

1. **Via tmsh on the BIG-IP:**

   ```bash
   ssh admin@<bigip-ip>
   tmsh list ltm profile client-ssl clientssl_demo_example_com cert-key-chain
   ```

   You should see the new versioned cert name.

2. **Via openssl (if you have a virtual server using the profile):**

   ```bash
   echo | openssl s_client -connect bigip-demo.example.com:443 -servername bigip-demo.example.com 2>/dev/null | openssl x509 -noout -dates -subject -issuer
   ```

   You should see:
   - Issuer: `Fake LE Intermediate X1` (staging) or `Let's Encrypt` (production)
   - Subject: `CN=bigip-demo.example.com`
   - notAfter: ~90 days from now

## Step 7: Test the renewal flow (no-op)

Run the playbook again immediately:

```bash
ansible-navigator run renew_f5_cert_v2.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  --mode stdout \
  --pae false \
  -i inventory/hosts.yml \
  -e @secrets.yml \
  -e cloudflare_zone=$CLOUDFLARE_ZONE
```

**Expected behavior:**

The pre-flight check finds the cert has 89+ days remaining (well above the
`cert_remaining_days: 30` threshold), so the play ends early:

```
TASK [Renewal decision] ********************************************************
ok: [bigip-demo.example.com] =>
  msg: Current cert on profile clientssl_demo_example_com valid for 89 more day(s); threshold is 30 — skipping renewal.

TASK [End play if the current cert is still fresh enough] *********************
skipping: [bigip-demo.example.com]
```

No ACME order, no BIG-IP changes. This is the behavior you want on a daily
schedule — almost every run no-ops.

## Step 8: Force a renewal (testing)

To exercise the full renewal flow without waiting 60 days:

```bash
ansible-navigator run renew_f5_cert_v2.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  --mode stdout \
  --pae false \
  -i inventory/hosts.yml \
  -e @secrets.yml \
  -e cloudflare_zone=$CLOUDFLARE_ZONE \
  -e cert_remaining_days=999
```

`cert_remaining_days=999` forces a renewal because the current cert has fewer
than 999 days left. The play will issue a fresh cert and update the profile.

**Rate limit warning:** Let's Encrypt production allows 5 duplicate certs per
week. If testing renewals repeatedly, use `-e acme_env=staging` (the default)
or wait a week between production renewals.

## Step 9: Switch to production certs

Once you've validated the flow with staging certs, switch to production:

```bash
ansible-navigator run renew_f5_cert_v2.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  --mode stdout \
  --pae false \
  -i inventory/hosts.yml \
  -e @secrets.yml \
  -e cloudflare_zone=$CLOUDFLARE_ZONE \
  -e acme_env=production
```

The new cert will be trusted by browsers. Verify:

```bash
curl -v https://bigip-demo.example.com 2>&1 | grep -E "subject:|issuer:"
```

You should see `issuer: C=US; O=Let's Encrypt; CN=...` with no certificate
errors.

## Step 10: Schedule it in AAP

1. Import the AAP configuration:

   ```bash
   ansible-navigator run ../../controller_setup/configure_aap.yml \
     -e aap_hostname=aap.example.com \
     -e aap_username=admin \
     -e aap_password='...' \
     -e aap_validate_certs=true
   ```

2. In the AAP UI:
   - Open **Credentials** → **Cloudflare** → paste your API token
   - Open **Credentials** → **F5 Admin** → paste your BIG-IP password
   - Navigate to **Job Templates** → **F5 / Renew certificate**
   - Launch it manually to verify it works
   - Check **Schedules** — a daily schedule is already configured

3. The job will run daily. Check the job output — almost every run will no-op
   at the pre-flight check. When the cert drops below 30 days remaining, the
   job automatically renews it.

## Rollback demo

If you want to test rollback:

1. Note the current cert name on the profile (e.g., `bigip_demo_example_com_20260602`)
2. Run a forced renewal to create a new cert (e.g., `..._20260603`)
3. Roll back to the previous cert:

   ```bash
   ansible-playbook rollback_f5_cert.yml \
     -i inventory/hosts.yml \
     -e @secrets.yml \
     -e previous_cert_name=bigip_demo_example_com_20260602
   ```

   (You'll need to create `rollback_f5_cert.yml` — see the README rollback
   section for the task example.)

## Cleanup

To remove the demo resources:

1. **On BIG-IP:**

   ```bash
   ssh admin@<bigip-ip>
   tmsh delete ltm virtual demo_vs
   tmsh delete ltm pool demo_pool
   tmsh delete ltm profile client-ssl clientssl_demo_example_com
   
   # Delete versioned cert objects
   tmsh list sys file ssl-cert | grep bigip_demo_example_com
   tmsh delete sys file ssl-cert bigip_demo_example_com_20260602.crt
   tmsh delete sys file ssl-key bigip_demo_example_com_20260602.key
   tmsh delete sys file ssl-cert bigip_demo_example_com_20260602_chain.crt
   
   tmsh save sys config
   ```

2. **In Cloudflare:** Delete the A record for `bigip-demo.example.com`

3. **Locally:** Remove secrets and ACME artifacts

   ```bash
   rm secrets.yml
   rm -rf .acme/
   ```

## Troubleshooting

**"No valid cert found on SSL profile" but you know a cert is there:**

Check that `clientssl_profile` variable matches the actual profile name on the
BIG-IP. The pre-flight query is case-sensitive.

**"Failed to validate the SSL certificate" when querying iControl REST:**

Set `f5_validate_certs: false` in your inventory host vars if the BIG-IP
management interface uses a self-signed cert.

**ACME challenge fails:**

- Verify the Cloudflare API token has correct permissions
- Check that `cloudflare_zone` matches the zone the FQDN lives in
- Wait 60s and retry — DNS propagation can be slow

**Profile update succeeds but virtual server still shows old cert:**

The profile was updated, but the virtual server might cache the old cert for
existing connections. New TLS handshakes will get the new cert immediately.
Check with a fresh `openssl s_client` connection.

## Next steps

- Add more BIG-IPs to the inventory
- Configure HA device group sync
- Integrate with your monitoring system to alert on cert expiry
- Set up AAP workflows for multi-device renewals with health checks

## Support

For issues or questions, open an issue at:
https://github.com/taruch/ansible-examples/issues
