# Patching Examples

A three-stage OS patching workflow for AAP — pre-patching checks, patch
application, post-patching validation — with a failure-branch rollback.
The workflow topology is always the same:

```
Pre-Patching Checks ──success──▶ Apply Patches ──success──▶ Post-Patching Validation
                                  Apply Patches ──failure──▶ Rollback
                                                  Post-Patching Validation ──failure──▶ Rollback
```

This directory demonstrates the same workflow two different ways.

## Two implementation styles

### 1. Standalone playbooks (currently wired into AAP via `setup.yml`)

Each stage is a single, self-contained playbook with all tasks written
inline — no roles involved. This is the easiest style to read top-to-bottom
for a demo, at the cost of duplicating logic across OS variants.

| Playbook | Stage | OS |
|---|---|---|
| [`pre_patching_playbook_linux.yml`](pre_patching_playbook_linux.yml) | Pre-Patching Checks | Linux |
| [`pre_patching_playbook_windows.yml`](pre_patching_playbook_windows.yml) | Pre-Patching Checks | Windows |
| [`patching_playbook.yml`](patching_playbook.yml) | Apply Patches (dnf) | Linux |
| [`post_patching_playbook.yml`](post_patching_playbook.yml) | Post-Patching Validation | Linux |
| [`rollback_playbook.yml`](rollback_playbook.yml) | Rollback (failure branch) | Linux |

There is no standalone Windows playbook yet for the Apply Patches, Post-Patching,
or Rollback stages — only Pre-Patching Checks has a Windows counterpart today.

### 2. Role-based, OS-aware playbooks (not yet wired into AAP)

Each stage also has a matching role under [`roles/`](roles/) that dispatches to
`linux.yml` or `windows.yml` based on `ansible_facts.os_family`, then runs a
`shared.yml` for the rest (reboot, service/application restoration, health
checks, monitoring maintenance mode, reporting) — branching internally by OS
wherever the module or check itself is platform-specific. A thin playbook just
calls the role:

| Playbook | Role | OS |
|---|---|---|
| [`pre_patching_role_playbook.yml`](pre_patching_role_playbook.yml) | `roles/pre_patching` | Linux + Windows |
| [`patching_role_playbook.yml`](patching_role_playbook.yml) | `roles/apply_patches` | Linux (dnf) + Windows (`win_updates`) |
| [`post_patching_role_playbook.yml`](post_patching_role_playbook.yml) | `roles/post_patching` | Linux + Windows |

This style is a single playbook per stage regardless of target OS — point it at
a mixed Linux/Windows inventory and each host runs its own branch automatically.

`roles/rollback/` exists as an empty stub — no rollback role or role-based
rollback playbook has been written yet.

Pick whichever style fits how you want to demo the workflow: standalone
playbooks read top-to-bottom with nothing hidden in a role; the role-based
playbooks are what you'd actually want in a mixed-OS fleet.

### Post-patch application validation (beyond "did it reboot")

`roles/post_patching`/`shared.yml` doesn't stop at confirming the host came
back from its reboot — it verifies the application on top actually came back
up:

- **Linux** — restores `services_to_start` via `ansible.builtin.service`,
  asserts each is `running` via `service_facts`, then checks
  `health_check_urls` (HTTP, via `ansible.builtin.uri`) and `tcp_health_checks`
  (port reachability).
- **Windows / IIS** — restores `services_to_start` via `ansible.windows.win_service`
  (e.g. `W3SVC`) and confirms each is `started` via `win_service_info`; sets
  `iis_app_pools_to_check` and `iis_sites_to_check` to `started` via
  `community.windows.win_iis_webapppool` / `win_iis_website` (self-healing if
  found stopped) and asserts the resulting state; then hits
  `iis_local_health_check_urls` (e.g. `http://localhost/`) with
  `ansible.windows.win_uri` **from the host itself** to confirm the site is
  actually serving traffic, not just that the service/app pool looks right.

  Note: `ansible.builtin.uri` doesn't run against Windows targets over WinRM
  (it's not one of the core modules ansible-core auto-redirects to a `win_*`
  equivalent), which is why Windows gets its own `win_uri`-based check instead
  of reusing `health_check_urls`.

All of the above are empty lists by default (no-op) — set them via survey/
`extra_vars` per target group. See
[`roles/post_patching/defaults/main.yml`](roles/post_patching/defaults/main.yml)
for the full variable list.

## Variables

Standalone playbooks declare their tunables directly in the play's `vars:`
block (see the header comment in each file for which ones to expose as an AAP
survey). Role-based playbooks take their defaults from the matching role:

- [`roles/pre_patching/defaults/main.yml`](roles/pre_patching/defaults/main.yml)
- [`roles/apply_patches/defaults/main.yml`](roles/apply_patches/defaults/main.yml)
- [`roles/post_patching/defaults/main.yml`](roles/post_patching/defaults/main.yml)

Override role defaults via survey/`extra_vars`, not by editing the role.

## Other files

- [`dnf_bulk_install_example.yml`](dnf_bulk_install_example.yml) / [`dnf_example_tasks.md`](dnf_example_tasks.md) — standalone notes on bulk-installing packages with dnf, including patterns for skipping packages that don't exist on a given host.

## AAP / Controller

[`setup.yml`](setup.yml) is the configuration-as-code file that registers this
example with AAP — a project, four job templates, and a workflow job template
that chains them with failure routing to rollback. It currently only
references the **standalone Linux** playbooks
(`pre_patching_playbook_linux.yml`, `patching_playbook.yml`,
`post_patching_playbook.yml`, `rollback_playbook.yml`). The Windows
pre-patching playbook and all three role-based playbooks are not yet
registered as job templates — add them to `controller_templates` /
`controller_workflows` in `setup.yml` if you want them available in AAP.

Apply it via `../controller_setup/configure_aap.yml` (or any wrapper that
`include_vars: setup.yml` and runs `infra.aap_configuration.dispatch`).
Requires a pre-existing Machine credential and inventory in AAP — set
`machine_credential` and `target_inventory` at the top of `setup.yml`.

## Running locally

```bash
ansible-playbook pre_patching_role_playbook.yml -e target_hosts=webservers
ansible-playbook patching_role_playbook.yml -e target_hosts=webservers -e dry_run=true
ansible-playbook post_patching_role_playbook.yml -e target_hosts=webservers
```

Or with `ansible-navigator` and an EE that bundles `ansible.windows`,
`community.vmware`, and `community.zabbix`:

```bash
ansible-navigator run -mstdout pre_patching_role_playbook.yml -e target_hosts=webservers
```
