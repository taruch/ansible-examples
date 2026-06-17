# letsencrypt_cloudflare

Acquires a Let's Encrypt certificate using the ACME DNS-01 challenge with TXT records written to a **Cloudflare**-managed zone.

All tasks `delegate_to: localhost` — the role expects to run from the control node regardless of which host the calling play targets. Useful when the play is targeting a remote host (e.g. a Windows host) but the cert work needs to happen locally.

## What it does

1. Generates an ACME account key (`account.key`) and a per-cert private key + CSR.
2. Starts an ACME order to obtain the DNS-01 challenge values.
3. Publishes `_acme-challenge` TXT records via `community.general.cloudflare_dns` (`solo: true` so a stale TXT from a previous run doesn't linger).
4. Tells ACME to validate, retrieves the cert, chain, and fullchain.
5. **Always** cleans up the TXT records afterward, even on failure.

After this role, the following files exist on the control node:

| File | Contents |
|---|---|
| `acme_account_key` | ACME account key (reused across runs) |
| `cert_key_path` | Per-cert private key |
| `cert_path` | Issued certificate (leaf only) |
| `chain_path` | Intermediate chain |
| `fullchain_path` | Leaf + chain concatenated |

A downstream role (e.g. `tomcat_windows_tls`) reads these to assemble a keystore.

## Required vars

| Var | Description |
|---|---|
| `cloudflare_zone` | Cloudflare-managed zone (e.g. `entrenchedrealist.dev`) |
| `cert_fqdn` | FQDN being issued; must live inside `cloudflare_zone` |
| `cloudflare_api_token` | API token with `Zone:DNS:Edit` + `Zone:Zone:Read` scoped to the zone. Defaults to `lookup('env', 'CLOUDFLARE_API_TOKEN')`. |

## Optional vars

| Var | Default | Description |
|---|---|---|
| `acme_env` | `staging` | Friendly switch: `staging` or `production`. Maps to `acme_directories[acme_env]`. |
| `acme_directories` | dict with staging + production URLs | Override only if you need a CA other than LE |
| `acme_directory` | derived from `acme_env` | Set this directly to override the directory URL outright (skips the env switch) |
| `cert_remaining_days` | `30` | Skip the ACME order if the existing cert has more than this many days left. Set to a value larger than the cert's max lifetime (e.g. `999`) to force re-issue. |
| `cert_name` | `cert_fqdn` with dots → underscores | Filename stem for cert artifacts |
| `acme_email` | `admin@{{ cloudflare_zone }}` | ACME account contact address |
| `acme_work_dir` | `{{ playbook_dir }}/.acme` | Where account key + per-cert files live |

## Requirements

- `community.crypto` and `community.general` collections (declared in `meta/main.yml`)
- Cloudflare API token — create at <https://dash.cloudflare.com/profile/api-tokens>:
  - Permissions: `Zone:Zone:Read` + `Zone:DNS:Edit`
  - Zone Resources: include the target zone only (least-privilege)

## Staging vs. production

Staging is the default. Flip to production at play time:

```bash
-e acme_env=production
```

Production limits to know:
- **5 duplicate certs / week** per identical FQDN set
- **5 failed validations / hour** per account+hostname
- **50 certs / week** per registered domain (eTLD+1)

`cert_remaining_days` (default `30`) makes the role idempotent: re-running within the window of validity short-circuits the order entirely and doesn't count against any limit. The semantics are "the cert must have at least N days left" — so to **force** a re-issue, pass a value *larger* than the cert's actual remaining validity (e.g. `cert_remaining_days=999`, since LE max is 90 days). Setting it to `0` means "any valid cert is fine" → never renew.

## Example

```yaml
- hosts: tomcat_windows_demo
  tasks:
    - ansible.builtin.include_role:
        name: letsencrypt_cloudflare
      vars:
        cloudflare_zone: entrenchedrealist.dev
        cert_fqdn: tomcat-demo.entrenchedrealist.dev
```
