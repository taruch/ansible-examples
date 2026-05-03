# Yum Update

Playbooks for applying package updates to RHEL/CentOS systems, with support for selective security and bugfix patching.

## Playbooks

### `site.yml`
Applies yum security and bugfix updates to all nodes. Uses the `yum` module with `security` and `bugfix` flags. Tagged for selective execution (`--tags security` or `--tags bugfix`).

### `security_updates.yml`
Installs security patches with additional logic:
- Gathers system facts before patching
- Supports both `yum` and `dnf` package managers
- Checks for required reboots after patching
- Conditionally reboots if `allow_reboot: true` is set

### `yum-update.yml`
General-purpose yum update playbook for full system package upgrades.

## Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `allow_reboot` | `false` | Set to `true` to automatically reboot after updates if required |

## Usage
```bash
# Security patches only
ansible-playbook site.yml --tags security

# Security patches with auto-reboot if needed
ansible-playbook security_updates.yml -e "allow_reboot=true"
```
