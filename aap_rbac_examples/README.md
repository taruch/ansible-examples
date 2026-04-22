# aap_rbac_examples

## org_inventory_sync.yml

Grants `Project Update` and `Inventory Update` roles to one or more teams for **all projects and inventories** within a given AAP organization. Useful for bulk-onboarding teams so they can trigger syncs without requiring admin access.

Compatible with **AAP 2.5 / 2.6** (gateway RBAC model).

### Collections required

- `ansible.controller`
- `infra.aap_configuration`

### Variables

| Variable | Default | Description |
|---|---|---|
| `target_org` | `Default` | Organization to scope resource discovery |
| `target_teams` | `[]` | **Required.** List of team names to receive roles |
| `aap_hostname` | `$CONTROLLER_HOST` | AAP controller hostname |
| `aap_username` | `$CONTROLLER_USERNAME` | AAP username |
| `aap_password` | `$CONTROLLER_PASSWORD` | AAP password |
| `aap_validate_certs` | `$CONTROLLER_VERIFY_SSL` | Validate TLS certificates |

Credentials can be supplied via vault variables (`vault_aap_*`) or environment variables. Vault variables take precedence.

### Usage

```bash
ansible-playbook org_inventory_sync.yml \
  -e target_org="My Org" \
  -e '{"target_teams": ["Ops Team", "Dev Team"]}' \
  -e @vault.yml --vault-password-file ~/.vault_pass
```

### What it does

1. Discovers all **projects** in `target_org` via the controller API
2. Discovers all **inventories** in `target_org` via the controller API
3. Grants `update` role on each project to all `target_teams`
4. Grants `update` role on each inventory to all `target_teams`
5. Prints a summary of what was applied

### Notes

- `target_teams` must be non-empty or the playbook will fail with a clear error message.
- Role assignments use `ansible.controller.role` rather than `ansible.platform.role_team_assignment` because resource-level roles (Project Update, Inventory Update) are not supported by the platform module.
- Running the playbook again is idempotent — existing role assignments are not duplicated.
