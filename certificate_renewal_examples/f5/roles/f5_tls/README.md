# f5_tls

Imports a Let's Encrypt certificate (issued by the `letsencrypt_cloudflare` role) into F5 BIG-IP and atomically updates the client-SSL profile to use it.

## What it does

1. Saves a UCS backup of the BIG-IP for rollback safety
2. Imports the cert private key with a versioned name (e.g., `example_com_20260602.key`)
3. Imports the certificate with a versioned name (e.g., `example_com_20260602.crt`)
4. Imports the intermediate chain (if present)
5. Updates the client-SSL profile to reference the new cert/key/chain (atomic swap, zero downtime)
6. Verifies the profile binding via `tmsh`
7. Saves the running config so changes survive a reboot

## Versioned object names

The role uses `{{ new_cert_object }}` (e.g., `wildcard_example_com_20260602`) as the base name for imported objects. This keeps the previous cert in place on the BIG-IP, making rollback a single profile update.

## Requirements

- `f5networks.f5_modules` collection (>= 1.32.0)
- Let's Encrypt cert artifacts at:
  - `{{ cert_path }}` (certificate)
  - `{{ cert_key_path }}` (private key)
  - `{{ chain_path }}` (intermediate chain)

These are automatically created by the `letsencrypt_cloudflare` role when run in the same play.

## Role Variables

See `defaults/main.yml` for the full list. Key vars:

| Variable | Default | Description |
|----------|---------|-------------|
| `cert_fqdn` | (required) | FQDN the cert was issued for |
| `new_cert_object` | (required) | Versioned base name for imported objects |
| `clientssl_profile` | (required) | Name of the client-SSL profile to update |
| `partition` | `Common` | BIG-IP partition |
| `provider` | (required) | F5 iControl REST provider dict (server, user, password) |
| `ucs_backup_dir` | `/tmp` | Where to save UCS backups |

## Example Playbook

```yaml
- name: Renew F5 cert via Let's Encrypt
  hosts: bigip
  connection: local
  roles:
    - role: letsencrypt_cloudflare
    - role: f5_tls
```

## Rollback

If the new cert causes issues, roll back by updating the profile to reference the previous cert:

```yaml
- name: Rollback F5 cert
  hosts: bigip
  connection: local
  tasks:
    - name: Revert client-SSL profile to previous cert
      f5networks.f5_modules.bigip_profile_client_ssl:
        name: "{{ clientssl_profile }}"
        partition: Common
        cert_key_chain:
          - cert: "{{ previous_cert_name }}.crt"
            key: "{{ previous_cert_name }}.key"
            chain: "{{ previous_cert_name }}_chain.crt"
        provider: "{{ provider }}"
```

Or restore the UCS backup:

```bash
# Upload the UCS file to the BIG-IP
scp /tmp/bigip01_pre_cert_renewal_20260602.ucs admin@bigip01:/var/local/ucs/

# Restore it (WARNING: reverts ALL config to the backup point)
tmsh load sys ucs /var/local/ucs/bigip01_pre_cert_renewal_20260602.ucs
```

## License

MIT

## Author

Todd Ruch
