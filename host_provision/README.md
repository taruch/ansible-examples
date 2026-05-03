# Host Provision

Playbooks for provisioning new hosts via Red Hat Satellite with base configuration applied automatically through AAP provisioning callbacks.

## How it works

1. The **Host Provision** job template runs `host_provision_config.yml`, which creates the VM in Satellite and triggers a PXE/Kickstart build.
2. The Kickstart finish script on the new host calls back to AAP using the provisioning callback URL configured on the **Host Base Config** job template.
3. AAP launches the **Host Base Config** job template against the host that checked in, applying base configuration automatically.

Run `setup.yml` once to configure both job templates and their dependencies in AAP.

## Playbooks

### `host_provision_config.yml`
Creates a new host in Red Hat Satellite and starts the PXE/Kickstart build. Runs against `localhost` using the Satellite API.

Variables required (via AAP survey or `-e`):

| Variable | Description |
|---|---|
| `Username` | Satellite admin username |
| `Password` | Satellite admin password |
| `Satellite_6_URL` | Satellite server URL |
| `vm_fqdn` | FQDN for the new host |

### `host_base_config.yml`
Applies base configuration to newly provisioned hosts. Intended to be triggered by the Satellite callback — not run directly. Runs the following roles:
- `create_ansible_user` — creates a dedicated Ansible service account for future remote automation
- `linux_pam` — enforces account lockout and password quality policy (see Roles section below)
- `motd` (optional, commented out) — deploys a custom message of the day

### `setup.yml`
Configuration as Code playbook that sets up the full Host Provision workflow in AAP. Run this once to create all required objects.

Creates:
- **Project** — SCM project pointing to this git repo
- **Inventory** — localhost inventory for Satellite API calls
- **Satellite Credential** — Satellite admin credentials
- **Machine Credential** — SSH key for newly provisioned hosts
- **Host Provision** job template — runs `host_provision_config.yml` with a survey for `vm_fqdn`
- **Host Base Config** job template — runs `host_base_config.yml` with `allow_simultaneous: true` and a provisioning callback key

Variables required for `setup.yml`:

| Variable | Description |
|---|---|
| `controller_hostname` | AAP controller URL |
| `controller_username` | AAP admin username |
| `controller_password` | AAP admin password |
| `scm_url` | Git repo URL for this project |
| `satellite_url` | Satellite server URL |
| `satellite_username` | Satellite admin username |
| `satellite_password` | Satellite admin password |
| `ssh_private_key` | Private key for SSH access to new hosts |
| `host_config_key` | Shared secret for the provisioning callback URL |

## Provisioning callback

After `setup.yml` runs, the callback URL for newly provisioned hosts is:

```
https://<aap_host>/api/controller/v2/job_templates/<id>/callback/
```

Add a curl call to the Kickstart finish script in Satellite:

```bash
curl -k -f -i -H 'Content-Type:application/json' \
  -XPOST https://<aap_host>/api/controller/v2/job_templates/<id>/callback/ \
  --data '{"host_config_key":"<host_config_key>"}'
```

The job template ID is shown in AAP after `setup.yml` completes.

## Roles

### `linux_pam`
Hardens the Linux PAM stack on newly provisioned RHEL hosts using `authselect` — the supported method for managing PAM profiles on RHEL 8/9 without editing PAM files directly.

**Use case:** Enforce a CIS-benchmark-aligned security baseline on every host at provision time, ensuring consistent policy before the host enters production.

Configures two PAM modules via their dedicated config files:

**`pam_faillock`** (`/etc/security/faillock.conf`) — account lockout policy:
- Lock accounts after 5 consecutive failed login attempts
- 15-minute automatic unlock window
- Policy applies to root as well (60-second root unlock to avoid full lockout)
- Failed attempts logged to syslog

**`pam_pwquality`** (`/etc/security/pwquality.conf`) — password complexity:
- Minimum 14-character length
- Requires digits, uppercase, lowercase, and special characters
- Rejects passwords with more than 3 consecutive identical characters
- Policy enforced even when root changes passwords

All values are configurable via role defaults. Key variables:

| Variable | Default | Description |
|---|---|---|
| `linux_pam_faillock_deny` | `5` | Failed attempts before lockout |
| `linux_pam_faillock_unlock_time` | `900` | Lockout duration in seconds |
| `linux_pam_faillock_even_deny_root` | `true` | Apply lockout to root |
| `linux_pam_pwquality_minlen` | `14` | Minimum password length |
| `linux_pam_pwquality_minclass` | `3` | Minimum character classes required |
| `linux_pam_authselect_profile` | `sssd` | authselect profile (`sssd` or `minimal`) |

## Requirements
- `redhat.satellite` collection
- `ansible.controller` collection
- Red Hat Satellite with a configured libvirt compute resource and hostgroup (`Default_Libvirt`)
- AAP 2.4+
