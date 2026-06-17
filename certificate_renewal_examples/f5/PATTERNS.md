# F5 Certificate Renewal Patterns

This directory contains two different approaches to F5 BIG-IP certificate renewal.
Choose the pattern that fits your workflow.

## Pattern Comparison

| Aspect | Pattern A (in-band LE) | Pattern B (pre-staged) |
|--------|------------------------|------------------------|
| **Playbook** | `renew_f5_cert_v2.yml` | `renew_f5_cert.yml` |
| **Cert source** | Automated Let's Encrypt DNS-01 | Manual files at `/etc/ansible/certs/` |
| **Pre-flight check** | ✅ Queries live cert from SSL profile | ❌ None |
| **Idempotent in AAP** | ✅ Yes (ephemeral filesystem safe) | ⚠️ Only if cert files persist |
| **Schedule-friendly** | ✅ Run daily, no-ops when fresh | ⚠️ Requires external "is it time?" logic |
| **Roles** | `letsencrypt_cloudflare` + `f5_tls` | Inline tasks only |
| **EE definition** | ✅ Complete (`ee/`) | ❌ Not provided |
| **AAP setup** | ✅ Config-as-code (`setup.yml`) | ❌ Not provided |
| **Demo guide** | ✅ `DEMO.md` | ❌ Not provided |
| **Dependencies** | `f5_modules`, `crypto`, `general` | `f5_modules`, `netcommon` |
| **Cloudflare required** | ✅ Yes (for DNS-01 challenge) | ❌ No |
| **Best for** | Automated renewals, AAP scheduling | Custom cert procurement workflows |

## When to use Pattern A (in-band LE)

- You want **set-it-and-forget-it** automation
- Cert is publicly resolvable and you control DNS in Cloudflare
- Running in **AAP** on a schedule (daily/weekly)
- Don't want to manually procure/stage cert files
- Want **zero manual intervention** for renewals

**Use:** `renew_f5_cert_v2.yml`

## When to use Pattern B (pre-staged)

- You have an **existing cert procurement process** (internal CA, external vendor)
- Cert files are delivered to you (e.g., via ticketing system, vault)
- You just need the **F5 import automation** (not the ACME issuance)
- Cert is internal-only or DNS is not in Cloudflare
- You manage cert expiry checks externally

**Use:** `renew_f5_cert.yml`

## Technical differences

### Pre-flight check

**Pattern A** queries the BIG-IP SSL profile via iControl REST API to get the
current cert's expiry timestamp. It computes days remaining and ends the play
early if the cert is still fresh (> `cert_remaining_days`). This makes the play
safe to run on a daily schedule — 29 out of 30 runs will be no-ops.

**Pattern B** has no pre-flight check. It assumes cert files exist at
`/etc/ansible/certs/{{ cert_name }}.{crt,key}` and blindly imports them. If you
run it twice with the same files, it's a no-op (F5 modules are idempotent), but
it doesn't check cert expiry first.

### ACME integration

**Pattern A** uses the `letsencrypt_cloudflare` role to:
1. Generate an ACME account key (or reuse existing)
2. Generate a certificate private key
3. Build a CSR for the FQDN
4. Start an ACME order with Let's Encrypt
5. Publish a `_acme-challenge` TXT record in Cloudflare
6. Wait for DNS propagation (polls Cloudflare's 1.1.1.1 resolver)
7. Tell LE to validate
8. Retrieve the issued cert + chain
9. Clean up the TXT record

All artifacts live in `.acme/{{ cert_fqdn }}/` on the control node (ephemeral
in AAP).

**Pattern B** expects you to provide the cert files manually. No ACME, no
Cloudflare, no DNS challenges.

### F5 import logic

Both patterns import cert/key/chain to BIG-IP with **versioned names** (e.g.,
`example_com_20260602.crt`) so the previous cert stays on disk for rollback.
Both update the client-SSL profile atomically (zero downtime).

**Pattern A** does this in the `f5_tls` role. **Pattern B** does it inline in
the playbook.

### Rollback

Both support rollback. Since objects are versioned, rolling back is a single
profile update:

```yaml
bigip_profile_client_ssl:
  name: clientssl_example_com
  cert_key_chain:
    - cert: example_com_20260520.crt
      key: example_com_20260520.key
      chain: example_com_20260520_chain.crt
```

See `rollback_f5_cert.yml` for a ready-to-run playbook.

### AAP / Controller integration

**Pattern A** includes `setup.yml` (config-as-code) that creates:
- Custom credential types for Cloudflare and F5
- Credentials (tokens/passwords left blank for user to fill)
- Execution environment
- Project (git)
- Inventory with demo hosts
- Job template
- Daily schedule

**Pattern B** doesn't include AAP setup. You'd need to create the job template,
credentials, and schedule manually.

## Migration path

If you're currently using **Pattern B** and want to move to **Pattern A**:

1. Ensure your cert FQDN is publicly resolvable and DNS is in Cloudflare
2. Create a Cloudflare API token (Zone:Zone:Read + Zone:DNS:Edit)
3. Switch your AAP job template to use `renew_f5_cert_v2.yml`
4. Add the Cloudflare credential to the template
5. Set `acme_env=staging` for first run (test with LE staging)
6. Validate the renewal works
7. Switch to `acme_env=production`

The pre-flight check means your first run will issue a fresh cert even if the
current cert is still valid (because the play doesn't know about the old cert's
expiry until it's imported). Subsequent runs will no-op correctly.

## File organization

```
f5/
├── renew_f5_cert_v2.yml       # Pattern A (in-band LE issuance)
├── renew_f5_cert.yml          # Pattern B (pre-staged certs)
├── rollback_f5_cert.yml       # Rollback playbook (works with both)
├── README_v2.md               # Pattern A documentation
├── README.md                  # Pattern B documentation (original)
├── DEMO.md                    # Pattern A demo walkthrough
├── PATTERNS.md                # This file
├── setup.yml                  # Pattern A AAP config-as-code
├── roles/
│   ├── letsencrypt_cloudflare/  # Pattern A only
│   └── f5_tls/                  # Pattern A only
└── ee/                        # Pattern A EE definition
```

## Support

For questions or issues, open a ticket at:
https://github.com/taruch/ansible-examples/issues

Choose the pattern that fits your environment and constraints. Both are
production-ready; the difference is where the cert comes from.
