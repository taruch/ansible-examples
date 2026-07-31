# F5 BIG-IP Certificate Renewal

Automated SSL certificate renewal for F5 BIG-IP load balancers with zero downtime.
Two patterns provided: **automated Let's Encrypt issuance** (Pattern A) or
**manual cert staging** (Pattern B).

## Quick Start

**For automated renewals via Let's Encrypt (recommended for AAP scheduling):**

```bash
ansible-navigator run renew_f5_cert_v2.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  -i inventory/hosts.yml \
  -e @secrets.yml \
  -e cloudflare_zone=example.com
```

**For manual cert staging (bring your own .crt/.key files):**

```bash
ansible-playbook -i inventory/hosts.yml renew_f5_cert.yml
```

## What's included

- ✅ **Zero-downtime cert rotation** (atomic SSL profile swap)
- ✅ **Versioned object names** (previous cert kept for rollback)
- ✅ **Pre-flight expiry check** (Pattern A only — no-ops if cert is fresh)
- ✅ **Let's Encrypt automation** (Pattern A only — DNS-01 via Cloudflare)
- ✅ **UCS backups** before changes
- ✅ **AAP configuration-as-code** (import with one command)
- ✅ **Execution Environment** (pre-built image on Quay)
- ✅ **Rollback playbook** (revert to previous cert with one command)

## Documentation

| Document | Purpose |
|----------|---------|
| [README_v2.md](README_v2.md) | **Pattern A** — Automated LE issuance (production guide) |
| [DEMO.md](DEMO.md) | **Pattern A** — Step-by-step demo walkthrough |
| [PATTERNS.md](PATTERNS.md) | Pattern A vs B comparison (choose the right one) |
| [roles/README.md](roles/README.md) | Role documentation |
| [ee/README.md](ee/README.md) | Execution Environment build guide |

## Pattern comparison

| Pattern | Cert source | Pre-flight check | Best for |
|---------|-------------|------------------|----------|
| **A** (`renew_f5_cert_v2.yml`) | Automated Let's Encrypt DNS-01 | ✅ Yes | AAP scheduling, hands-off renewals |
| **B** (`renew_f5_cert.yml`) | Manual files at `/etc/ansible/certs/` | ❌ No | Custom cert workflows, internal CAs |

See [PATTERNS.md](PATTERNS.md) for detailed comparison.

## Architecture (Pattern A)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Pre-flight: Query BIG-IP SSL profile for cert expiry    │
│    ↓ If cert has < 30 days left, continue. Else, end play. │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Issue cert: Let's Encrypt DNS-01 via Cloudflare         │
│    • Generate ACME account key + cert private key          │
│    • Start ACME order, publish _acme-challenge TXT record  │
│    • Wait for DNS propagation, validate, retrieve cert     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Import to BIG-IP: Upload cert/key/chain (versioned)     │
│    • Save UCS backup                                        │
│    • Import as example_com_20260602.{crt,key}              │
│    • Update client-SSL profile (atomic swap)               │
│    • Verify, save config                                   │
└─────────────────────────────────────────────────────────────┘
```

F5 BIG-IP swaps SSL profiles with **zero connection drops** — active TLS sessions
continue on the old cert; new handshakes get the new cert immediately.

## Requirements

- **F5 BIG-IP** (physical, VE, or cloud) with iControl REST API access
- **Ansible 2.15+** or ansible-navigator with EE support
- **Cloudflare-managed DNS** (Pattern A only) with API token
- **Collections** (bundled in EE or install via `requirements.yml`):
  - `f5networks.f5_modules` >= 1.32.0
  - `community.crypto` >= 2.22.0
  - `community.general` >= 10.0.0
  - `ansible.netcommon` >= 7.0.0

## Installation

### Option 1: Use the pre-built Execution Environment (recommended)

```bash
# Pull the image
podman pull quay.io/truch/f5-cert-renewal:1.0

# Run with ansible-navigator
ansible-navigator run renew_f5_cert_v2.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  -i inventory/hosts.yml \
  -e @secrets.yml \
  -e cloudflare_zone=example.com
```

All dependencies are pre-installed in the image.

### Option 2: Use system Ansible

```bash
# Install collections
ansible-galaxy collection install -r requirements.yml

# Run the playbook
ansible-playbook -i inventory/hosts.yml renew_f5_cert_v2.yml \
  -e @secrets.yml \
  -e cloudflare_zone=example.com
```

## Configuration

### 1. Inventory

Edit `inventory/hosts.yml`:

```yaml
all:
  children:
    bigip:
      hosts:
        bigip01.example.com:
          ansible_host: 10.1.1.100          # BIG-IP management IP
          f5_validate_certs: false          # true if mgmt cert is valid
          clientssl_profile: clientssl_wildcard_example_com
          partition: Common
```

### 2. Secrets

Create `secrets.yml` (gitignored):

```yaml
---
# Pattern A (Let's Encrypt)
cloudflare_api_token: "YOUR_CLOUDFLARE_API_TOKEN"
f5_user: admin
f5_password: "YOUR_BIGIP_PASSWORD"

# Pattern B (manual certs) — only f5_user/f5_password needed
```

Get a Cloudflare API token at https://dash.cloudflare.com/profile/api-tokens
with `Zone:Zone:Read` + `Zone:DNS:Edit` permissions.

### 3. Variables

Key variables (pass via `-e` or inventory):

| Variable | Default | Description |
|----------|---------|-------------|
| `cert_fqdn` | `inventory_hostname` | FQDN to issue cert for |
| `cloudflare_zone` | (required for Pattern A) | Cloudflare DNS zone |
| `acme_env` | `staging` | `staging` or `production` |
| `cert_remaining_days` | `30` | Skip renewal if cert has more days left |
| `clientssl_profile` | `clientssl_{{ cert_name }}` | Client-SSL profile name |
| `partition` | `Common` | BIG-IP partition |

## Usage Examples

### Daily scheduled renewal (Pattern A)

```bash
# First run — issues a fresh cert
ansible-navigator run renew_f5_cert_v2.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  -i inventory/hosts.yml \
  -e @secrets.yml \
  -e cloudflare_zone=example.com \
  -e acme_env=production

# Subsequent runs (daily schedule) — no-ops if cert has >30 days left
# Run this on a daily schedule; 29/30 runs will end at pre-flight check
```

### Force a renewal (testing)

```bash
ansible-navigator run renew_f5_cert_v2.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  -i inventory/hosts.yml \
  -e @secrets.yml \
  -e cloudflare_zone=example.com \
  -e cert_remaining_days=999  # Force renewal regardless of expiry
```

### Manual cert import (Pattern B)

```bash
# Stage cert files on control node
mkdir -p /etc/ansible/certs
cp wildcard_example_com.crt /etc/ansible/certs/
cp wildcard_example_com.key /etc/ansible/certs/
cp wildcard_example_com_chain.crt /etc/ansible/certs/

# Run the playbook
ansible-playbook -i inventory/hosts.yml renew_f5_cert.yml \
  -e cert_name=wildcard_example_com \
  -e clientssl_profile=clientssl_wildcard_example_com
```

### Rollback to previous cert

```bash
ansible-playbook rollback_f5_cert.yml \
  -i inventory/hosts.yml \
  -e @secrets.yml \
  -e previous_cert_name=example_com_20260520
```

## AAP / Automation Controller Setup

Import the configuration-as-code in one command:

```bash
ansible-navigator run ../../controller_setup/configure_aap.yml \
  -e aap_hostname=aap.example.com \
  -e aap_username=admin \
  -e aap_password='your_password' \
  -e aap_validate_certs=true
```

This creates:
- ✅ Credential types (Cloudflare, F5 BIG-IP)
- ✅ Credentials (fill in tokens/passwords in AAP UI after import)
- ✅ Execution environment (points to Quay image)
- ✅ Project (git repo)
- ✅ Inventory with demo hosts
- ✅ Job template
- ✅ Daily schedule

Then just fill in your Cloudflare token and F5 password in the AAP UI. The job
is ready to run.

## How it works

### Pre-flight check (Pattern A only)

The playbook queries the BIG-IP client-SSL profile via iControl REST API to get
the currently-active certificate's expiration timestamp. If the cert has more
than `cert_remaining_days` (default 30) remaining, the play ends immediately —
no ACME order, no BIG-IP changes.

This makes the playbook **safe to run daily**. Almost every run will be a no-op.
Once the cert drops below the threshold (~60 days before expiry for a 90-day LE
cert), the next run automatically renews it.

### Versioned object names

Certs are imported with versioned names like `example_com_20260602.crt`. This
keeps the previous cert on the BIG-IP for **instant rollback** — just update the
profile to reference the old cert name.

### Zero downtime

F5's `bigip_profile_client_ssl` module updates the profile atomically. Existing
TLS sessions continue using the old cert; new handshakes immediately get the new
cert. No connection drops, no service interruption.

## Rollback

If a renewal causes issues:

### Option 1: Profile rollback (instant)

```bash
ansible-playbook rollback_f5_cert.yml \
  -i inventory/hosts.yml \
  -e @secrets.yml \
  -e previous_cert_name=example_com_20260520
```

This reverts the client-SSL profile to the previous cert. Takes ~2 seconds.

### Option 2: UCS restore (full config rollback)

```bash
# Upload the UCS backup (created before renewal)
scp /tmp/bigip01_pre_cert_renewal_20260602.ucs admin@bigip01:/var/local/ucs/

# Restore it on BIG-IP
tmsh load sys ucs /var/local/ucs/bigip01_pre_cert_renewal_20260602.ucs
```

⚠️ **WARNING:** UCS restore reverts **ALL** config to the backup point, not just
the cert. Use profile rollback unless you need full config recovery.

## Troubleshooting

**"No valid cert found on SSL profile" but I know a cert is there:**

- Check `clientssl_profile` variable matches the actual profile name (case-sensitive)
- Verify the profile has a cert-key-chain configured (run `tmsh list ltm profile client-ssl <name>`)

**ACME validation fails:**

- Verify Cloudflare API token has correct permissions (Zone:Zone:Read + Zone:DNS:Edit)
- Check `cloudflare_zone` matches the zone the FQDN lives in
- Wait 60s and retry — DNS propagation can be slow

**"SSL: CERTIFICATE_VERIFY_FAILED" when connecting to BIG-IP:**

- Set `f5_validate_certs: false` in inventory if BIG-IP mgmt interface has self-signed cert
- Or install the BIG-IP's CA cert in the EE's trust store

**Rate limit hit (Let's Encrypt):**

- Default `acme_env=staging` is unlimited — use this for testing
- Production has 5 duplicate certs/week limit per FQDN set
- Set `cert_remaining_days=30` to avoid unnecessary renewals

## HA Pairs and ConfigSync

For active/standby F5 pairs:

**Option 1:** Run against the active device only; let ConfigSync replicate

**Option 2:** Run against both devices and add a sync task:

```yaml
- name: Sync to device group
  f5networks.f5_modules.bigip_configsync_action:
    device_group: my-device-group
    sync_device_to_group: true
    provider: "{{ provider }}"
```

## Rate Limits (Let's Encrypt)

Let's Encrypt production limits:
- **5 duplicate certs / week** per identical FQDN set
- **5 failed validations / hour** per account+hostname
- **50 certs / week** per registered domain (eTLD+1)

With `cert_remaining_days: 30`, a single F5 issues ~4 certs/year. Well under
the limits.

Use `acme_env=staging` for testing — unlimited issuances.

## File Structure

```
f5/
├── README.md                       # This file
├── README_v2.md                    # Pattern A detailed guide
├── DEMO.md                         # Step-by-step demo walkthrough
├── PATTERNS.md                     # Pattern A vs B comparison
├── renew_f5_cert_v2.yml            # Pattern A orchestrator (LE + F5)
├── renew_f5_cert.yml               # Pattern B orchestrator (manual certs)
├── rollback_f5_cert.yml            # Rollback playbook
├── setup.yml                       # AAP config-as-code
├── requirements.yml                # Ansible collections
├── ansible.cfg                     # Project config
├── ansible-navigator.yml           # Navigator config
├── inventory/
│   ├── hosts.yml                   # Production inventory
│   └── host_vars/
│       └── bigip01.example.com.yml # Per-host variables
├── roles/
│   ├── README.md                   # Role documentation
│   ├── letsencrypt_cloudflare/     # ACME DNS-01 role (Pattern A)
│   └── f5_tls/                     # F5 import role (Pattern A)
└── ee/
    ├── README.md                   # EE build guide
    ├── execution-environment.yml   # EE definition
    ├── requirements.yml            # Collections
    ├── bindep.txt                  # System packages
    └── files/
        └── ansible.cfg             # Baked into EE
```

## Support

- **Issues/Questions:** https://github.com/taruch/ansible-examples/issues
- **Docs:** See README_v2.md, DEMO.md, PATTERNS.md
- **AAP:** https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/

## License

MIT

## Author

Todd Ruch

---

**Next steps:**

1. Read [DEMO.md](DEMO.md) for a step-by-step walkthrough
2. Choose your pattern in [PATTERNS.md](PATTERNS.md)
3. Follow [README_v2.md](README_v2.md) for production deployment
4. Import [setup.yml](setup.yml) into AAP for instant scheduling
