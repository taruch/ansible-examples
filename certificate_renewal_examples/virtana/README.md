# Virtana Appliance Certificate Renewal

Renews the SSL certificate on Virtana appliances (Infrastructure Observability /
VirtualWisdom) via SSH. Virtana does not expose certificate management through
its public REST API, so this playbook connects to the appliance over SSH and
uses the appropriate CLI method for your appliance version.

## Vendor Documentation

- [IO Administrator Guide — Certificate Management](https://docs.virtana.com/en/infrastructure-observability/io-administrator-guide/installation-and-configuration/appliance-configuration/certificate-management.html) — Appliance certificate configuration (navigate to Appliance Configuration > Certificate Management)
- [Exporting a Certificate (IO Virtual Edition)](https://docs.virtana.com/en/infrastructure-observability-docs/io-virtual-edition-guide/completing-the-configuration-checklist/exporting-a-certificate.html) — Certificate export/import for IO integration trust
- [Public API](https://docs.virtana.com/en/public-api.html) — API reference (confirms certificate management is not available via API)

**Important:** Virtana appliance architectures vary significantly by product and
version. The exact certificate update procedure depends on your specific
appliance. Consult the Virtana IO Administrator Guide for your version before
running this playbook. The three methods below cover the most common
configurations, but your environment may differ.

## Supported Methods

This playbook supports three methods — set `appliance_type` to match your
environment:

| `appliance_type` | Method | Appliance Type |
|-------------------|--------|----------------|
| `virtana_config` | `virtana-config --update-ssl` CLI utility | Modern IO appliances |
| `k3s` | `kubectl create secret tls` | Global View / Platform appliances running K3s |
| `legacy` | File replacement + nginx restart | Older VirtualWisdom appliances |

## What it does

1. Validates the new cert/key files on the control node and reads cert metadata.
2. Copies the cert, key, and chain to the appliance.
3. Backs up the current certificate configuration.
4. Applies the new certificate using the selected method:
   - **virtana_config:** Runs `virtana-config --update-ssl` and restarts nginx
   - **k3s:** Replaces the Kubernetes TLS secret and restarts deployments
   - **legacy:** Copies cert/key files to the standard paths and restarts nginx/virtana-web
5. Waits for the web interface to come back up.
6. Verifies the served certificate matches the uploaded one.
7. Cleans up temporary files on the appliance.

## Requirements

- SSH access to the Virtana appliance with sudo/root privileges
- `community.crypto` collection
- For `k3s` method: `kubectl` available on the appliance

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

# Run the playbook (defaults to virtana_config method)
ansible-playbook -i inventory/hosts.yml renew_virtana_cert.yml

# Use a specific method
ansible-playbook -i inventory/hosts.yml renew_virtana_cert.yml \
  -e appliance_type=k3s

ansible-playbook -i inventory/hosts.yml renew_virtana_cert.yml \
  -e appliance_type=legacy
```

### Target a specific appliance

```bash
ansible-playbook -i inventory/hosts.yml renew_virtana_cert.yml \
  --limit virtana01.example.com
```

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `appliance_type` | `virtana_config` | Method to use: `virtana_config`, `k3s`, or `legacy` |
| `cert_src` | `files/<hostname>.crt` | Path to the signed certificate |
| `key_src` | `files/<hostname>.key` | Path to the private key |
| `chain_src` | `files/<hostname>_chain.crt` | Path to CA chain (optional) |
| `legacy_cert_dir` | `/etc/pki/tls/certs` | Cert directory for legacy method |
| `legacy_key_dir` | `/etc/pki/tls/private` | Key directory for legacy method |
| `k3s_namespace` | `default` | Kubernetes namespace for K3s method |
| `k3s_secret_name` | `virtana-tls` | TLS secret name for K3s method |

## Rollback

The playbook creates timestamped backups before making changes.

**virtana_config method:**
```bash
# Restore backed-up cert files
cp -a /opt/virtana/backups/certs_<date>/* /etc/pki/tls/certs/
cp -a /opt/virtana/backups/private_<date>/* /etc/pki/tls/private/
systemctl restart nginx
```

**k3s method:**
```bash
# Restore the backed-up Kubernetes secret
kubectl apply -f /opt/virtana/backups/virtana-tls_<date>.yaml
kubectl rollout restart deployment -n default
```

**legacy method:**
```bash
# Backup copies are created by Ansible's backup: true option
# Check /etc/pki/tls/certs/ and /etc/pki/tls/private/ for .bak files
systemctl restart nginx virtana-web
```

## Important Notes

- **Verify your method first:** SSH to the appliance and check which components
  are present before choosing a method:
  - `which virtana-config` — if found, use `virtana_config`
  - `which kubectl && kubectl get nodes` — if K3s is running, use `k3s`
  - `systemctl status nginx` — if nginx serves the UI directly, use `legacy`
- **Cert file paths may vary:** Legacy VirtualWisdom appliances may store certs
  in `/etc/nginx/certs/` instead of `/etc/pki/tls/`. Check your appliance and
  override `legacy_cert_dir` / `legacy_key_dir` as needed.
- **No REST API:** Virtana's public API covers alerts, topology, and dashboards
  but does not include certificate management endpoints.

## AAP / Controller

Create a Job Template with:
- **Credential:** Machine credential with SSH access to the Virtana appliance
- **Survey:** Add `appliance_type` as a choice list (`virtana_config`, `k3s`,
  `legacy`) so operators can select the correct method at launch time
