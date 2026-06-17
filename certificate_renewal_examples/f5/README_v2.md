# F5 BIG-IP Certificate Renewal with Let's Encrypt

Renews an SSL certificate on F5 BIG-IP via Let's Encrypt and atomically swaps the
client-SSL profile to use it. Designed to run on a schedule (AAP, cron, etc.) and
**issue the cert in-band** via Let's Encrypt — no pre-staged cert files required.

## Architecture (Pattern A — in-band LE issuance)

`renew_f5_cert_v2.yml` is a thin orchestrator over two roles:

1. **Pre-flight on the BIG-IP.** Query the current client-SSL profile via iControl
   REST API to get the active cert's expiry. If the cert has more than
   `cert_remaining_days` left (default `30`), the play ends early — no ACME order,
   no profile update. This check is what makes the play idempotent in **AAP**,
   where the project filesystem is ephemeral and `.acme/` never persists between
   job runs.

2. **Issue (or refresh) the cert.** `letsencrypt_cloudflare` runs a DNS-01
   challenge against your Cloudflare zone. The new cert lives only inside the
   EE's ephemeral filesystem.

3. **Import and rotate.** `f5_tls` imports the cert/key/chain to BIG-IP with
   versioned names (e.g., `example_com_20260602.crt`), updates the client-SSL
   profile to reference them (atomic zero-downtime swap), and saves the config.

F5 BIG-IP hot-swaps SSL profiles with no connection drops — the rotation is
seamless.

## Schedule it

Point an AAP job template (or any scheduler) at `renew_f5_cert_v2.yml` and run it
daily or weekly. Each run:

- Almost always no-ops (live cert is still fresh).
- Becomes a real renewal once the live cert is within `cert_remaining_days` of
  expiry — at which point it issues, imports, and swaps in a single job.

No need for a separate "is it time?" check; the play is the check.

## Rate limits

Let's Encrypt production caps to remember:
- **5 duplicate certs / week** per identical FQDN set
- **5 failed validations / hour** per account+hostname
- **50 certs / week** per registered domain (eTLD+1)

The default `cert_remaining_days: 30` keeps you well clear: a single F5 issues
~4 certs/year against production. Iterating against the same FQDN under
production should use `-e acme_env=production -e cert_remaining_days=999` only
when you genuinely want a fresh issuance — and even then only intentionally.
The default `acme_env=staging` gives you effectively unlimited issuances for
development.

## Required vars

| Var | Source | Notes |
|---|---|---|
| `cloudflare_zone` | extra-var / inventory | Zone the cert FQDN lives in |
| `cloudflare_api_token` | env `CLOUDFLARE_API_TOKEN`, extra-var, or AAP credential injector | `Zone:Zone:Read` + `Zone:DNS:Edit`, zone-scoped |
| `f5_user` | inventory / vault / AAP credential | BIG-IP admin username |
| `f5_password` | inventory / vault / AAP credential | BIG-IP admin password |

## Optional vars (with defaults)

| Var | Default | Purpose |
|---|---|---|
| `cert_fqdn` | `inventory_hostname` | FQDN to issue for. The inventory hostname IS the cert by default. |
| `acme_env` | `staging` | Set to `production` for a real trusted cert. |
| `cert_remaining_days` | `30` | Skip renewal when live cert has more than this many days left. Set to `999` to force re-issue. |
| `clientssl_profile` | `clientssl_{{ cert_name }}` | Name of the client-SSL profile to update. |
| `partition` | `Common` | BIG-IP partition where cert objects live. |
| `f5_validate_certs` | `true` | Validate BIG-IP's management cert (set false for self-signed). |
| `f5_server_port` | `443` | iControl REST API port. |

## Layout

```
f5/
├── README_v2.md                    # this file — production renewal flow
├── DEMO.md                         # demo bootstrap walkthrough
├── renew_f5_cert_v2.yml            # Pattern A orchestrator (LE issuance + F5 import)
├── renew_f5_cert.yml               # Original Pattern B (pre-staged certs)
├── requirements.yml                # collections (f5networks.f5_modules, community.crypto, etc.)
├── ansible.cfg                     # roles_path = ./roles
├── inventory/
│   ├── hosts.yml                   # production inventory
│   └── host_vars/
│       └── bigip01.example.com.yml # per-host vars
├── ee/                             # Execution Environment definition
├── setup.yml                       # AAP configuration-as-code (import this)
└── roles/
    ├── letsencrypt_cloudflare/     # localhost: ACME DNS-01 via Cloudflare
    └── f5_tls/                     # localhost: import to BIG-IP, update SSL profile
```

## Execution Environment

A pre-built image will be published on Quay:

```
quay.io/truch/f5-cert-renewal:1.0
quay.io/truch/f5-cert-renewal:latest
```

Source for the EE definition lives in [`ee/`](ee/README.md). It bundles the
required collections (`f5networks.f5_modules`, `ansible.netcommon`,
`community.crypto`, `community.general`), Python deps (`f5-sdk`, `bigsuds`,
`cryptography`, `requests`), and is built on
`registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel9:latest`.

To rebuild from source:

```bash
cd ee
ansible-builder build --tag f5-cert-renewal:<tag> -v3
```

## Running locally with ansible-navigator

```bash
ansible-navigator run renew_f5_cert_v2.yml \
  --eei quay.io/truch/f5-cert-renewal:1.0 \
  --pull-policy missing \
  --mode stdout \
  --pae false \
  -i inventory/hosts.yml \
  -e @secrets.yml \
  -e cloudflare_zone=example.com
```

`secrets.yml` (gitignored) holds the Cloudflare token + F5 admin credentials.
Each BIG-IP's management IP lives in `inventory/hosts.yml` as `ansible_host`.
The play targets the `bigip` group.

Defaults to LE staging. For a real trusted cert add `-e acme_env=production`.

## AAP / Controller

The fastest path is the configuration-as-code file shipped with this example:
[`setup.yml`](setup.yml). It defines the credential types, credentials, EE,
project, inventory + hosts + group, job templates, and a daily schedule. Apply
it via `../../controller_setup/configure_aap.yml` (which runs
`infra.aap_configuration.dispatch`):

```bash
ansible-navigator run ../../controller_setup/configure_aap.yml \
  -e aap_hostname=aap.example.com \
  -e aap_username=admin \
  -e aap_password='...' \
  -e aap_validate_certs=true
```

You then only need to:

1. Open the **Cloudflare** credential in AAP and paste the actual API token
   (it's left blank in the import).
2. Open the **F5 Admin** credential in AAP and paste the BIG-IP admin password.

What `setup.yml` creates:

- A custom credential type `Cloudflare API Token` that injects both
  `CLOUDFLARE_API_TOKEN` (env) and `cloudflare_api_token` (extra-var)
- A custom credential type `F5 BIG-IP Credentials` that injects `f5_user` and
  `f5_password` as extra-vars
- An execution environment pointing at the Quay image
- A git project at `https://github.com/taruch/ansible-examples.git`
- An inventory `F5 BIG-IP Demo` with hosts under the `bigip` group
- A job template `F5 / Renew certificate`
- A daily schedule on the renewal template (cheap since the pre-flight no-ops
  when certs are fresh)

### Workflow for production renewals

F5 swaps SSL profiles with zero downtime, so no drain/restore workflow is
needed. The play can run against an active BIG-IP in an HA pair. If running
against both devices, consider:

1. Run against the active device and let ConfigSync replicate, or
2. Run against both in sequence and add a `bigip_configsync_action` task to
   sync the device group.

## Rollback

If a renewal goes bad and you need to revert, the previous cert is still on
the BIG-IP (versioned object names). Rollback is a single task:

```yaml
- name: Rollback F5 cert
  hosts: bigip
  connection: local
  tasks:
    - name: Revert client-SSL profile to previous cert
      f5networks.f5_modules.bigip_profile_client_ssl:
        name: clientssl_example_com
        partition: Common
        cert_key_chain:
          - cert: example_com_20260520.crt
            key: example_com_20260520.key
            chain: example_com_20260520_chain.crt
        provider:
          server: "{{ ansible_host }}"
          user: "{{ f5_user }}"
          password: "{{ f5_password }}"
          validate_certs: false
```

Or restore the UCS backup created before the renewal:

```bash
scp /tmp/bigip01_pre_cert_renewal_20260602.ucs admin@bigip01:/var/local/ucs/
# On BIG-IP:
tmsh load sys ucs /var/local/ucs/bigip01_pre_cert_renewal_20260602.ucs
```

**WARNING:** UCS restore reverts ALL config to the backup point, not just the cert.

## Pattern comparison

This repo includes two F5 cert renewal patterns:

| File | Pattern | Cert source | Pre-flight check | AAP-ready |
|------|---------|-------------|------------------|-----------|
| `renew_f5_cert.yml` | B (pre-staged) | Manual cert files at `/etc/ansible/certs/` | ❌ No | ⚠️ Partial |
| `renew_f5_cert_v2.yml` | A (in-band LE) | Automated Let's Encrypt DNS-01 | ✅ Yes | ✅ Yes |

Use **Pattern A** (`renew_f5_cert_v2.yml`) for automated renewals on a schedule.
Use **Pattern B** (`renew_f5_cert.yml`) when you have an existing cert
procurement process and just need the BIG-IP import automation.

## HA pairs and ConfigSync

If targeting an active/standby pair:

1. **Option 1:** Run the play against only the active device and let BIG-IP's
   ConfigSync replicate the change to the standby.

2. **Option 2:** Run against both devices sequentially and add a
   `bigip_configsync_action` task to force a sync:

```yaml
- name: Sync to device group
  f5networks.f5_modules.bigip_configsync_action:
    device_group: my-device-group
    sync_device_to_group: true
    provider: "{{ provider }}"
```

## Demo environment

To exercise this against a real BIG-IP, see [`DEMO.md`](DEMO.md). You bring a
BIG-IP instance (physical, VE, or cloud) and a Cloudflare-managed zone;
everything else is automated. The same `renew_f5_cert_v2.yml` then runs against
the demo host to exercise the renewal flow.
