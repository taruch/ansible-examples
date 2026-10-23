# Per-Host CyberArk Credentials for Ansible/AAP

## Problem

AAP Job Templates (and `job_templates_launch_create` via the API/MCP tools) accept
exactly **one** Machine credential per launch. CyberArk, by contrast, is commonly
configured with one vaulted account **per target host**
(`Safe=LINUX_SERVERS;Object=<hostname>-admin` or similar). There's no way to attach
N per-host credentials to a single job template, and AAP's built-in CyberArk CCP
Lookup credential type (wired via `controller_credential_input_sources`, see
`../IaC_testing/roles/aap_configuration_extended/aap_configuration_extended/tests/configs/custom/credential_input_sources.yml`)
only supports a **static** `object_query` — it resolves one secret into one target
AAP credential, not one secret per inventory host.

## Options considered

1. **One AAP credential + `credential_input_sources` per host, one Job Template per
   host.** Works, but doesn't scale (N job templates / N credentials for N hosts)
   and defeats the point of running one play against a dynamic inventory.
2. **Dynamic inventory plugin that calls CyberArk at sync time** and writes
   `ansible_password` into hostvars. Works, but caches the secret for the life of
   the sync interval, which fights CyberArk's rotation / check-out model if
   secrets are short-lived or one-time-use.
3. **In-play per-host lookup (chosen).** Resolve the secret inside the play, per
   host, at the moment it's needed, by calling CyberArk's Central Credential
   Provider (CCP) REST API directly from a `vars`/`group_vars` Jinja expression.

## The reframe

Same insight as `../windows_examples/wsman_mapping_credential_options.md`: the AAP
Machine credential doesn't have to *be* the password used to log into the host —
it only has to be whatever AAP needs in order to resolve the real credential. For
the Windows cert-mapping case that was a client certificate (an indirection table
on the target). For CyberArk it's a single API identity (app ID, optionally a
client cert for mutual TLS) used to talk to CyberArk's CCP web service — not a
login credential for any target host at all.

That means:

- **One** AAP credential, of a custom "CyberArk CCP Connection" type, holds only
  what's needed to authenticate to CyberArk's CCP REST service (`url`, `app_id`,
  optionally a client cert). This is the thing that satisfies "AAP job templates
  accept one credential."
- The **per-host** secret is never stored in AAP at all. It's fetched inside the
  play, scoped to the current `inventory_hostname`, and used immediately to set
  `ansible_password` / `ansible_become_password` for that host's connection.

## Implementation

### 1. Naming convention

Pick (or confirm with whoever administers the CyberArk Safes) a deterministic
mapping from inventory hostname to CyberArk Safe/Object, e.g.:

```
Safe=LINUX_SERVERS
Object={{ inventory_hostname }}-admin
```

If the convention isn't a clean string template, add an explicit
`cyberark_account_object` host var per host instead of concatenating
`inventory_hostname`.

### 2. One-time AAP credential

See `setup_aap_credential.yml` — registers a custom credential type that stores
only CCP connection details (URL, app ID, client cert) and creates one credential
of that type. This is what gets attached to the Job Template as extra vars; it is
**not** what logs into target hosts.

### 3. Per-host resolution

Two valid implementations — see "Correction" below for why both work and how to
choose between them:

- `set_per_host_credential_tasks.yml` (Option A, recommended default) — retrieves
  the secret as the first task of the play via CyberArk's official
  `cyberark.pas.cyberark_credential` module, then `set_fact`s it onto the host
  before any task that needs a real connection.
- `group_vars_example/all.yml` (Option B) — wires `ansible_password` directly to
  a lookup templated on `inventory_hostname`, with no extra collection required.

### 4. Standalone test

`get_cyberark_credential.yml` is a `localhost`-only demo (same pattern as
`../Azure_Key_Vault_examples/get_secret_from_vault.yml`) for validating CCP
connectivity / app ID / Safe permissions before wiring the lookup into real
inventory.

## Correction (recorded 2026-10-23, from user pushback)

An earlier draft of this doc argued that CyberArk's official `cyberark.pas`
collection (module `cyberark_credential`) couldn't be used here because modules
only run as tasks, not inside `group_vars`/`host_vars`, and that this reintroduced
a "fetch-before-connect" ordering problem. **That reasoning was wrong.** A
task-based retrieval works fine as the *first task* of the play, delegated to
`localhost` (so it needs no connection to the target), followed by `set_fact` on
the real host — later tasks in the same play pick up the freshly set connection
var before they need to connect. The only real ordering constraint is Ansible's
*implicit* fact-gathering, which runs before your first explicit task unless
`gather_facts: false` is set; with that disabled, there's no ordering problem at
all. Two implementations are both valid — pick based on the tradeoffs below.

### Option A: task-based, using CyberArk's official collection (recommended default)

```yaml
- hosts: target_hosts
  gather_facts: false
  tasks:
    - name: Retrieve this host's account from CyberArk CCP
      cyberark.pas.cyberark_credential:
        api_base_url: "{{ cyberark_ccp_url }}"
        app_id: "{{ cyberark_ccp_app_id }}"
        query: "Safe=LINUX_SERVERS;Object={{ inventory_hostname }}-admin"
        client_cert: "{{ cyberark_ccp_client_cert | default(omit) }}"
        client_key: "{{ cyberark_ccp_client_key | default(omit) }}"
      register: cyberark_result
      delegate_to: localhost
      no_log: true

    - name: Apply the retrieved password for this host's connection
      ansible.builtin.set_fact:
        ansible_password: "{{ cyberark_result.password }}"
      no_log: true

    - name: Now safe to gather facts / run real work
      ansible.builtin.setup:
```

See `set_per_host_credential_tasks.yml`. Pros: uses CyberArk's officially
maintained module (parameter names, auth, retries, and error handling are
CyberArk's problem to keep correct, not this repo's). Cons: every play that
targets CyberArk-backed hosts needs these as its first two tasks (a role or
`pre_tasks` import makes this a one-line include rather than copy/paste), and the
`cyberark.pas` collection must be installed in the Execution Environment.

### Option B: vars-level REST lookup, no extra collection

What's in `group_vars_example/all.yml` — resolves `ansible_password` directly
from `group_vars`/`host_vars` via `ansible.builtin.url`, calling CyberArk's CCP
REST endpoint (`GET /AIMWebService/api/Accounts?AppID=...&Safe=...&Object=...`)
directly. Any play that targets the host gets the right credential automatically,
with nothing to remember to add per-playbook, and no dependency on the
`cyberark.pas` collection being present in the EE. Trade-off: it's a hand-built
call against CyberArk's REST API rather than a maintained module, so the exact
path/parameter names/casing need verifying against your CCP version before
production use (`AIMWebService` vs a newer `CCP` path; separate `Safe`/`Object`
params vs a combined `Query=Safe=...;Object=...` param — this has varied across
CyberArk versions). If your CCP requires mutual TLS, confirm whether it's AAP's
execution node or the CyberArk Credential Provider agent that owns the client
certificate.

**Recommendation:** use Option A if the `cyberark.pas` collection is available
and credential retrieval can live in a shared role/`pre_tasks`. Fall back to
Option B only if that collection can't be added to the EE.

## Security notes

- Always `no_log: true` on any task that could expose the resolved secret (`debug`,
  `set_fact`, etc.) — `get_cyberark_credential.yml` deliberately leaves the
  "print the password" task commented out to show what *not* to leave enabled.
- Scope the CCP Application ID used by AAP (in CyberArk) to only the Safes/Objects
  the automation actually needs — least privilege now lives on the vault side,
  since AAP no longer gatekeeps which per-host secret gets used.
- If CyberArk enforces short-lived or one-time-use credentials, the in-play lookup
  (option 3) is required — options 1 and 2 would serve a stale or
  already-checked-in secret.
- Verify CCP's TLS certificate (`validate_certs: true`) rather than disabling
  verification — the secret travels over this connection.

## Requirements

- `ansible.controller` collection (or `awx.awx` for older AAP/Tower) — only for
  `setup_aap_credential.yml`, the one-time credential-type/credential registration.
- No extra collection is required for the per-host lookup itself —
  `ansible.builtin.url` ships with `ansible-core`.
- CyberArk CCP reachable over HTTPS from wherever the lookup runs (the Execution
  Environment, for a real job).

## Unresolved / verify before production

- Confirm the CCP REST path and query parameters against your CyberArk version
  (see "Why a raw REST call" above).
- Confirm whether your CCP deployment requires mutual TLS (client cert) or
  API-key-style auth for the `app_id`, and adjust `setup_aap_credential.yml`'s
  injectors accordingly.
- If using `ansible_become_password` instead of `ansible_password` (host already
  reachable via SSH key, CyberArk only guards privilege escalation), the per-host
  lookup pattern is identical — just target the become var in
  `group_vars_example/all.yml`.
