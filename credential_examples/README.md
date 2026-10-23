# Credential Examples

Patterns for cases where AAP's "one credential per Job Template" model doesn't
line up with how an external secrets system is actually set up.

## `per_host_cyberark_credentials.md`

CyberArk is often configured with one vaulted account **per target host**, but an
AAP Job Template only accepts one Machine credential per launch. This doc works
through the options and lands on resolving the secret per host, inside the play,
via a direct call to CyberArk's Central Credential Provider (CCP) REST API — the
same reframe used in `../windows_examples/wsman_mapping_credential_options.md`:
the AAP credential only needs to authenticate to the system that resolves the
real secret, not be the real secret itself.

- `setup_aap_credential.yml` — one-time registration of a custom AAP credential
  type that stores CyberArk CCP connection details (not a host password).
- `get_cyberark_credential.yml` — standalone `localhost` test of CCP connectivity
  and the Safe/Object naming convention, before wiring it into real inventory.
- `set_per_host_credential_tasks.yml` (Option A, recommended default) — resolves
  the per-host secret as the first task of a play, via CyberArk's official
  `cyberark.pas.cyberark_credential` module, before any task needs a real
  connection to the target.
- `group_vars_example/all.yml` (Option B) — resolves `ansible_password` per host
  directly from `group_vars`/`host_vars` via a lookup, no extra collection
  required.

## Requirements

- `ansible.controller` collection (or `awx.awx`) — only for
  `setup_aap_credential.yml`.
- `cyberark.pas` collection — only for Option A
  (`set_per_host_credential_tasks.yml`).
- No extra collection for Option B — it uses `ansible.builtin.url`, which ships
  with `ansible-core`.
- CyberArk CCP reachable over HTTPS from wherever the lookup/module runs.

## See Also

- `../windows_examples/wsman_mapping_credential_options.md` — the analogous
  per-host-credential problem for Windows WinRM, and the "indirection, not
  password replacement" insight this directory reuses.
- `../Azure_Key_Vault_examples/` — simpler single-secret lookup pattern this
  directory's standalone test playbook follows.
