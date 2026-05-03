# Windows Kerberos

Comprehensive Kerberos debugging and validation playbook for troubleshooting WinRM Kerberos authentication to Windows hosts.

## Playbooks

### `test_kerberos.yml`
Validates the full Kerberos authentication chain step by step:

1. Verifies `/etc/krb5.conf` configuration
2. Resolves DNS SRV records for the KDC
3. Tests TCP connectivity to the KDC on port 88
4. Runs `kinit` with `KRB5_TRACE` debug output to obtain a ticket
5. Displays the Kerberos ticket cache via `klist`

## Required Variables
| Variable | Description |
|----------|-------------|
| `krb_principal` | Kerberos principal (e.g., `user@DOMAIN.COM`) |
| `krb_password` | Principal password |
| `krb_realm` | Kerberos realm (e.g., `DOMAIN.COM`) |
| `kdc_hostname` | KDC hostname or IP |

## Prerequisites on Ansible Controller
```bash
# RHEL/CentOS
dnf install krb5-workstation

# Ubuntu/Debian
apt install krb5-user python3-gssapi
```

## Usage
```bash
ansible-playbook test_kerberos.yml -e "krb_principal=admin@DOMAIN.COM krb_password=secret krb_realm=DOMAIN.COM kdc_hostname=dc01.domain.com"
```
