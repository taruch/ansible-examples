# Virtana Appliance Certificate Renewal

Renews the SSL certificate on Virtana appliances (Infrastructure Observability /
VirtualWisdom) via SSH. Virtana does not expose certificate management through
its REST API, so this playbook connects to the appliance over SSH, backs up the
Java keystore, imports the new certificate via `keytool`, and restarts services.

## What it does

1. Validates the new cert/key files on the control node and reads cert metadata.
2. Backs up the current Java keystore on the appliance.
3. Creates a PKCS12 bundle from the new cert + key on the control node using
   `community.crypto.openssl_pkcs12`.
4. Copies the PKCS12 bundle to the appliance and imports it into the Java
   keystore via `keytool -importkeystore`.
5. Optionally imports the CA chain into the keystore.
6. Restarts Virtana services to apply the new certificate.
7. Waits for the web interface to come back up and verifies the served
   certificate matches the uploaded one.
8. Cleans up temporary files on the appliance.

## Requirements

- SSH access to the Virtana appliance with sudo/root privileges
- Java `keytool` available on the appliance (ships with the Virtana installation)
- `community.crypto` collection

```bash
ansible-galaxy collection install -r requirements.yml
```

## Layout

```
virtana/
├── README.md
├── renew_virtana_cert.yml
├── requirements.yml
├── files/                              # drop cert material here
│   ├── virtana01_example_com.crt       # signed certificate (PEM)
│   ├── virtana01_example_com.key       # private key (PEM)
│   └── virtana01_example_com_chain.crt # CA chain (PEM, optional)
└── inventory/
    └── hosts.yml
```

## Usage

```bash
# Place cert material in files/
cp signed_cert.crt files/virtana01_example_com.crt
cp private_key.key files/virtana01_example_com.key
cp ca_chain.crt files/virtana01_example_com_chain.crt

# Run the playbook
ansible-playbook -i inventory/hosts.yml renew_virtana_cert.yml
```

### Target a specific appliance

```bash
ansible-playbook -i inventory/hosts.yml renew_virtana_cert.yml \
  --limit virtana01.example.com
```

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `cert_src` | `files/<hostname>.crt` | Path to the signed certificate |
| `key_src` | `files/<hostname>.key` | Path to the private key |
| `chain_src` | `files/<hostname>_chain.crt` | Path to CA chain (optional) |
| `virtana_home` | `/opt/virtana` | Virtana installation directory |
| `keystore_path` | `<virtana_home>/conf/keystore.jks` | Java keystore path |
| `keystore_password` | `changeit` | Keystore password (vault this in production) |
| `keystore_alias` | `virtana` | Alias for the certificate in the keystore |
| `virtana_services` | `[virtana, virtana-proxy]` | Services to restart after renewal |

## Rollback

The playbook creates a timestamped backup of the keystore before making changes.
To rollback:

```bash
# On the appliance
cp /opt/virtana/backups/keystore.jks.<date> /opt/virtana/conf/keystore.jks
systemctl restart virtana virtana-proxy
```

Or use the rollback as a playbook extra var:

```bash
ansible-playbook -i inventory/hosts.yml renew_virtana_cert.yml \
  -e restore_backup=true -e backup_date=2026-08-01
```

## Important Notes

- **Keystore path and password:** The defaults assume a standard Virtana
  installation. Check your appliance's actual keystore location and password.
  Consult the Virtana IO Administrator Guide under Appliance Configuration >
  Certificate Management for your specific version.
- **Service names:** The default service names (`virtana`, `virtana-proxy`) may
  differ on your installation. Verify with `systemctl list-units 'virtana*'` on
  the appliance.
- **No REST API:** Virtana's public API covers alerts, topology, and dashboards
  but does not include certificate management endpoints. This playbook uses SSH
  and `keytool` as the supported path.
- **Vault the keystore password:** In production, store `keystore_password` in
  Ansible Vault or an AAP credential rather than in plaintext variables.

## AAP / Controller

Create a Job Template with:
- **Credential:** Machine credential with SSH access to the Virtana appliance
- **Extra Variables:** Override `keystore_password` (ideally via a custom
  credential type that injects it as a variable)
- **Survey:** Add `cert_name` for flexibility across multiple appliances
