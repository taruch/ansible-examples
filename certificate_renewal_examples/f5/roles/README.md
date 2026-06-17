# F5 Certificate Renewal Roles

This directory contains Ansible roles for automated F5 BIG-IP certificate renewal
via Let's Encrypt.

## Roles

### letsencrypt_cloudflare

Issues (or renews) a certificate via Let's Encrypt using the DNS-01 challenge
against a Cloudflare-managed zone.

**What it does:**
- Generates an ACME account key (or reuses existing)
- Generates a certificate private key
- Builds a CSR for the requested FQDN
- Starts an ACME order
- Publishes `_acme-challenge` TXT records in Cloudflare
- Waits for DNS propagation
- Validates the challenge
- Retrieves the certificate and chain
- Cleans up TXT records

**Requirements:**
- `community.crypto` collection
- `community.general` collection
- Cloudflare API token with Zone:Zone:Read + Zone:DNS:Edit permissions

**Outputs:**
- `{{ acme_work_dir }}/{{ cert_fqdn }}/cert.pem` — Certificate
- `{{ acme_work_dir }}/{{ cert_fqdn }}/key.pem` — Private key
- `{{ acme_work_dir }}/{{ cert_fqdn }}/chain.pem` — Intermediate chain
- `{{ acme_work_dir }}/{{ cert_fqdn }}/fullchain.pem` — Certificate + chain

**Key variables:**
- `cert_fqdn` (required) — FQDN to issue the cert for
- `cloudflare_zone` (required) — Cloudflare zone the FQDN lives in
- `cloudflare_api_token` (required) — API token
- `acme_env` (default: `staging`) — `staging` or `production`
- `cert_remaining_days` (default: `30`) — Skip if cert has more days left

See [letsencrypt_cloudflare/README.md](letsencrypt_cloudflare/README.md).

---

### f5_tls

Imports a Let's Encrypt certificate into F5 BIG-IP and atomically updates the
client-SSL profile to use it.

**What it does:**
- Saves a UCS backup for rollback
- Imports cert/key/chain with versioned names (e.g., `example_com_20260602.crt`)
- Updates the client-SSL profile (zero-downtime cutover)
- Verifies the profile binding
- Saves the running config

**Requirements:**
- `f5networks.f5_modules` collection (>= 1.32.0)
- Cert artifacts from `letsencrypt_cloudflare` role

**Key variables:**
- `cert_fqdn` (required) — FQDN the cert was issued for
- `new_cert_object` (required) — Versioned base name for imported objects
- `clientssl_profile` (required) — Name of the client-SSL profile to update
- `provider` (required) — F5 iControl REST provider dict
- `partition` (default: `Common`) — BIG-IP partition

See [f5_tls/README.md](f5_tls/README.md).

---

## Usage

These roles are designed to run in sequence:

```yaml
- name: Renew F5 cert via Let's Encrypt
  hosts: bigip
  connection: local
  roles:
    - role: letsencrypt_cloudflare
    - role: f5_tls
```

The first role issues the cert on the control node; the second role imports it
to the BIG-IP.

## Standalone use

Both roles can be used independently:

**Use `letsencrypt_cloudflare` alone** if you just need Let's Encrypt cert
issuance (not F5-specific):

```yaml
- name: Issue a cert
  hosts: localhost
  roles:
    - role: letsencrypt_cloudflare
      vars:
        cert_fqdn: example.com
        cloudflare_zone: example.com
```

**Use `f5_tls` alone** if you already have cert artifacts (from another source):

```yaml
- name: Import cert to F5
  hosts: bigip
  connection: local
  roles:
    - role: f5_tls
      vars:
        cert_fqdn: example.com
        new_cert_object: example_com_20260602
        cert_path: /tmp/cert.pem
        cert_key_path: /tmp/key.pem
        chain_path: /tmp/chain.pem
```

## Testing

To test `letsencrypt_cloudflare` in isolation:

```bash
ansible-playbook -i localhost, -c local test_le_only.yml \
  -e cert_fqdn=test.example.com \
  -e cloudflare_zone=example.com \
  -e cloudflare_api_token=YOUR_TOKEN \
  -e acme_env=staging
```

Where `test_le_only.yml` is:

```yaml
---
- hosts: localhost
  roles:
    - letsencrypt_cloudflare
```

Check for cert artifacts in `.acme/test.example.com/`.

## Dependencies

Install required collections:

```bash
ansible-galaxy collection install -r ../requirements.yml
```

Or use the pre-built Execution Environment which bundles everything.

## License

MIT

## Author

Todd Ruch
