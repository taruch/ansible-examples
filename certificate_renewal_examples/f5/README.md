# F5 BIG-IP Certificate Renewal

Renews an SSL certificate on a BIG-IP LTM and atomically swaps the client-SSL
profile to use it. Designed to run without dropping the VIP.

## What it does

1. Pre-flight checks that the new cert and key files exist locally.
2. Saves a UCS backup of the device for rollback.
3. Imports the new cert, key, and chain under a versioned object name
   (e.g. `wildcard_example_com_2026-05-11.crt`) so the previous cert stays in
   place.
4. Updates the existing client-SSL profile to reference the new cert/key/chain.
   This is the single cutover moment; existing TLS sessions drain naturally.
5. Verifies the profile binding via `tmsh`.
6. Saves running config so the change survives a reboot.

## Rollback

Because objects are versioned, rolling back is one task:

```yaml
- name: Roll back to previous cert
  f5networks.f5_modules.bigip_profile_client_ssl:
    name: clientssl_wildcard_example_com
    cert_key_chain:
      - cert: wildcard_example_com_2026-04-11.crt
        key:  wildcard_example_com_2026-04-11.key
        chain: wildcard_example_com_2026-04-11_chain.crt
    provider: "{{ provider }}"
```

## Layout

```
f5/
├── README.md
├── renew_f5_cert.yml          # the playbook
├── requirements.yml           # f5networks.f5_modules
└── inventory/
    ├── hosts.yml
    └── host_vars/
        └── bigip01.example.com.yml
```

## Prerequisites

```bash
ansible-galaxy collection install -r requirements.yml
```

Place the renewed cert material on the control node:

```
/etc/ansible/certs/wildcard_example_com.crt
/etc/ansible/certs/wildcard_example_com.key
/etc/ansible/certs/wildcard_example_com_chain.crt
```

Set credentials (or use a vault / AAP credential):

```bash
export F5_USER=admin
export F5_PASSWORD='...'
```

## Usage

```bash
ansible-playbook -i inventory/hosts.yml renew_f5_cert.yml
```

Override defaults at the CLI:

```bash
ansible-playbook -i inventory/hosts.yml renew_f5_cert.yml \
  -e cert_name=api_example_com \
  -e clientssl_profile=clientssl_api_example_com
```

## HA pairs

If running against an active/standby pair, target only the active device and
let ConfigSync replicate, or add a post-task using
`f5networks.f5_modules.bigip_configsync_action` to push to the device group.

## AAP / Controller

Wrap this with a Job Template and a Machine credential for the BIG-IP login.
A surveyed `cert_name` makes the same template reusable across every cert you
manage.
