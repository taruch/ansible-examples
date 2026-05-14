# demo_prep

Control-node prep for the Tomcat-on-Windows certificate-renewal demo:
builds the demo WAR once and upserts a per-host Cloudflare A record.

Designed to be invoked from a **Windows-host-targeting play** — its tasks
delegate to `localhost` internally and use the targeted host's
`ansible_host` (from inventory) as the A record value, so the role
scales to multiple hosts without any per-run extra-vars.

## What it does

1. Asserts `cloudflare_zone`, `cert_fqdn`, `cloudflare_api_token`, and the
   current host's `ansible_host` are set.
2. Packages `files/webapp/` into `hello.war` at `war_path` (default
   `{{ playbook_dir }}/files/hello.war`) using `community.general.archive`.
   `run_once: true` so the WAR is built once and shared across hosts.
3. Upserts a Cloudflare A record `<cert_fqdn>` → `<ansible_host>`
   (TTL 60, `solo: true` so re-runs replace any prior record). Runs per host.

## Required vars

| Var | Description |
|---|---|
| `cloudflare_zone` | Cloudflare-managed zone (e.g. `entrenchedrealist.dev`) |
| `cert_fqdn` | FQDN of the demo app, must live inside `cloudflare_zone` |
| `cloudflare_api_token` | Cloudflare API token with `Zone:DNS:Edit` + `Zone:Zone:Read` scoped to the zone. Defaults to `lookup('env', 'CLOUDFLARE_API_TOKEN')`. |
| `ansible_host` | Each targeted host's public IP (set in inventory). Used as the A record value. |

## Optional vars

| Var | Default | Description |
|---|---|---|
| `war_path` | `{{ playbook_dir }}/files/hello.war` | Where the built WAR is written |

## Requirements

- `community.general` collection (declared in `meta/main.yml`)
- A Cloudflare API token created at <https://dash.cloudflare.com/profile/api-tokens> with the two permissions above, scoped to the zone you're using

## Example

```yaml
- hosts: tomcat_windows_demo       # Windows hosts; demo_prep delegates to localhost
  gather_facts: true
  vars:
    cert_fqdn: "{{ inventory_hostname }}"
  roles:
    - role: demo_prep
      vars:
        cloudflare_zone: entrenchedrealist.dev
```
