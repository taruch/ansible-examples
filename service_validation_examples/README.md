# Service Validation

Hourly drift check for a Windows service. If the service is found stopped,
the playbook restarts it and opens a ServiceNow incident describing what
was done plus the last interactive user on the host (read from Security
log event 4624).

Designed to run on a schedule against many hosts. The hot path — service
already running — exits via `end_host` before any non-Windows tasks, so
healthy hosts complete in seconds and never touch ServiceNow.

## Files

| File | Purpose |
|---|---|
| [`ensure_service.yml`](ensure_service.yml) | Scheduled Windows check. `win_service_info` → end_host if running → `win_service: started` → SNOW incident with last 4624 logon. |
| [`ensure_linux_service.yml`](ensure_linux_service.yml) | Scheduled Linux check. `systemd_service: started` → end_host if unchanged → SNOW incident with last user from `wtmp`. |
| [`deploy_service_demo.yml`](deploy_service_demo.yml) | One-shot setup playbook. Installs a fake `AnsibleDemoSvc` you can stop/start to demo drift. Windows → NSSM-wrapped PowerShell loop; Linux → systemd-wrapped bash loop. OS detected per host via `ansible_system`. |
| [`inventory/demo.yml`](inventory/demo.yml) | Demo inventory (two Windows hosts). |
| [`setup.yml`](setup.yml) | AAP 2.6 CaC: SNOW credential type, EE, project, inventory, template, hourly schedule. |

## Demo flow

```bash
# 1. Stand up the fake service on every host (idempotent)
ansible-navigator run deploy_service_demo.yml -i inventory/demo.yml ...

# 2. Point the validation play at the fake service instead of Tomcat10
#    (set in inventory, group_vars, or -e service_name=AnsibleDemoSvc)

# 3. RDP / ssh in and stop the service
#    Windows: Stop-Service AnsibleDemoSvc
#    Linux:   sudo systemctl stop AnsibleDemoSvc

# 4. Wait for the hourly schedule (or launch the template manually)
#    → ensure_service.yml restarts it + opens a SNOW incident
```

## Required vars

| Var | Source | Notes |
|---|---|---|
| `service_name` | inventory / group_vars / extra-var | Windows service name to check. Default `Tomcat10`. |
| `SN_HOST` / `SN_USERNAME` / `SN_PASSWORD` | AAP "ServiceNow" credential (env injection) | `servicenow.itsm.*` reads these from env. |
| `ansible_password` | AAP Machine credential | Windows admin password. |

## Optional vars

| Var | Default | Purpose |
|---|---|---|
| `snow_caller` | `aap_system` | Value for the incident's `caller` field. |

## Local run

```bash
ansible-navigator run ensure_service.yml \
  --eei <ee_with_ansible_windows_and_servicenow.itsm> \
  --mode stdout \
  --pae false \
  -i inventory/demo.yml \
  -e SN_HOST=https://your-instance.service-now.com \
  -e SN_USERNAME='aap_integration' \
  -e SN_PASSWORD='...' \
  -e ansible_password='...'
```

(In AAP, the SNOW + Machine credentials handle these variables for you.)

## AAP deployment

```bash
ansible-navigator run ../controller_setup/configure_aap.yml \
  -e @setup.yml \
  -e aap_hostname=aap.example.com \
  -e aap_username=admin \
  -e aap_password='...' \
  -e aap_validate_certs=true
```

(Or any wrapper that `include_vars: setup.yml` and runs
`infra.aap_configuration.dispatch`.)

Pre-existing credentials this expects in AAP (NOT created by `setup.yml`):

- Machine credential **`Demo Credential`** — Windows admin user/password
- Custom credential **`ServiceNow_Credential`** — injecting `SN_HOST`,
  `SN_USERNAME`, `SN_PASSWORD` as env vars

If your credentials are named differently, edit the `windows_machine_credential`
and `snow_credential` tunables at the top of `setup.yml`.

Other check:

- Verify the **EE** referenced at `ee_image` has both `ansible.windows`
  and `servicenow.itsm`. If you're on a different EE, edit the tunable
  at the top of `setup.yml`.

The schedule is enabled and runs hourly at the top of the hour by
default. Adjust the rrule in `controller_schedules` for a different
cadence or maintenance window.

## How "efficient" was achieved

- `gather_facts: false` — skips `win_setup` (saves a roundtrip per host)
- `end_host` on the happy path — healthy hosts finish after two tasks
  (check + decision), no SNOW connection opened
- `servicenow.itsm.incident` reads connection info from env vars
  (injected by the credential type) — no extra API call
- Parallel by default (`forks: 10` on the template) — hundreds of hosts
  complete in seconds total when nothing is wrong
- No retries, no `wait_for`, no `pause`

## What lands in the ServiceNow incident

- **Short description:** `Auto-remediated: service '<name>' restarted on <host>`
- **Description body:** prior state, current state, start mode, display
  name, last interactive user (from Security log event 4624 — filtered to
  exclude SYSTEM/LOCAL SERVICE/NETWORK SERVICE etc.)
- **Impact / Urgency:** `low` / `low` (override in the play if you want
  this paged differently)
- **Caller:** `aap_system` by default — override via `snow_caller`
