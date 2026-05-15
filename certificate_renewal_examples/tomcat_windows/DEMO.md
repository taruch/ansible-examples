# Demo environment — Tomcat on Windows

Stands up everything `renew_tomcat_cert.yml` needs to be demoed against a real
host: Apache Tomcat running as a Windows service, a tiny `hello.war`, and an
initial **Let's Encrypt** certificate (via DNS-01 against a Cloudflare zone)
wired into the TLS connector.

Two playbooks live at this directory level:

| File | Run when | What it does |
|------|----------|--------------|
| `demo_host_init.yml` | Once per Windows host | Builds the WAR, creates the Cloudflare A record, installs Java + Tomcat, issues the initial LE cert, configures the TLS connector. |
| `renew_tomcat_cert.yml` | On a schedule | Pre-flight: read live cert expiry. If close to expiry, re-issue via LE and ship to Tomcat. Otherwise no-op. See [`README.md`](README.md). |

You launch the Windows EC2 instance yourself and have a Cloudflare-managed
domain ready (e.g. `entrenchedrealist.dev`).

## Prerequisites

### Execution Environment (recommended)

A pre-built EE is on Quay:

```
quay.io/truch/tomcat-windows-cert-renewal:1.1
```

It bundles `ansible.windows`, `community.windows`, `community.crypto`,
`community.general` plus `pywinrm[credssp]`, `cryptography`, `requests`. The
WAR is built via `community.general.archive`, so no `zip` binary is required.

To rebuild from source, see [`ee/README.md`](ee/README.md).

### Cloudflare API token

The demo writes one A record and (briefly) a `_acme-challenge` TXT record into
your Cloudflare zone. Create a scoped API token at
<https://dash.cloudflare.com/profile/api-tokens> with:

- **Permissions:** `Zone:Zone:Read` + `Zone:DNS:Edit`
- **Zone Resources:** include only the zone you're using (least-privilege)

Then provide it to the play. Three options:

```bash
# 1) Env var, passed through ansible-navigator
export CLOUDFLARE_API_TOKEN='cf-token-here'
ansible-navigator run demo_host_init.yml --penv CLOUDFLARE_API_TOKEN ...

# 2) Extra-var inline (avoid for real tokens; appears in artifact cache unless --pae false)
ansible-navigator run demo_host_init.yml -e cloudflare_api_token='cf-token-here' ...

# 3) secrets.yml file (gitignored) — recommended for local iteration
ansible-navigator run demo_host_init.yml -e @secrets.yml ...
```

`secrets.yml` at this directory level is the gitignored convention used by the
roles. Populate it with the Cloudflare token and Windows admin password — both
are picked up by the playbook automatically via `-e @secrets.yml`.

In AAP, store the token as either:

1. **Vault credential** containing `cloudflare_api_token: !vault ...`
2. **Custom credential type** with input `cloudflare_api_token` and
   `injectors.env.CLOUDFLARE_API_TOKEN` — cleaner UX.

### Inventory

`inventory/demo.yml` is the demo-style inventory (CredSSP, self-signed WinRM
cert tolerated, real demo host). The shipped template targets
`tomcat-demo.entrenchedrealist.dev` — replace with the FQDN you want issued
inside your Cloudflare zone. The inventory hostname IS the cert FQDN (the play
reads `inventory_hostname` as the default for `cert_fqdn`).

Set each host's public IP in the inventory file as `ansible_host`. The
playbook is multi-host capable — add as many host entries as you like
(each with its own FQDN + `ansible_host`). The Cloudflare A record for
each host is upserted automatically from `ansible_host`.

```yaml
tomcat_windows_demo:
  hosts:
    tomcat-demo.entrenchedrealist.dev:
      ansible_host: 203.0.113.10
    tomcat-demo-2.entrenchedrealist.dev:
      ansible_host: 198.51.100.20
```

`inventory/hosts.yml` is a separate production-style template (Kerberos,
`validate_certs`) for non-demo deployments.

### Alternative — system ansible

If you'd rather run locally without an EE:

```bash
ansible-galaxy collection install -r requirements.yml
```

The Cloudflare module hits the API directly using the token from your env or
extra-vars; no extra CLI tools are needed.

---

## Step 1 — Have a Cloudflare-managed zone ready

You need a domain whose DNS is managed by Cloudflare (e.g.
`entrenchedrealist.dev`). If you registered the domain elsewhere, add it to
Cloudflare and switch the registrar's nameservers to the two Cloudflare NSes
listed in your zone's Overview page — that's the only Cloudflare setup the
demo requires.

Pick a hostname inside that zone for the demo app (e.g.
`tomcat-demo.entrenchedrealist.dev`). You don't need to create the A record
yourself — `demo_host_init.yml` does that.

---

## Step 2 — Launch the Windows EC2 instance (manual)

1. **AMI:** Windows Server 2022 (or 2019), `t3.medium` or larger.
2. **Security group inbound:**
   - `8443/tcp` from anywhere (or your IP) — HTTPS to the demo app
   - `5986/tcp` from your IP — WinRM over HTTPS
   - `3389/tcp` from your IP — RDP (optional)
   - `8080/tcp` from your IP — optional, Tomcat HTTP (only if you want it)
   - **No port 80 required** — DNS-01 doesn't use HTTP.
3. **WinRM:** enable WinRM-over-HTTPS at launch with the standard bootstrap
   script as user data:
   <https://github.com/ansible/ansible-documentation/blob/devel/examples/scripts/ConfigureRemotingForAnsible.ps1>
4. Decrypt the Administrator password in the EC2 console; note the **public IP**.

---

## Step 3 — Run `demo_host_init.yml`

### From the EE with ansible-navigator (recommended)

```bash
ansible-navigator run demo_host_init.yml \
  --eei quay.io/truch/tomcat-windows-cert-renewal:1.1 \
  --pull-policy missing \
  --mode stdout \
  --pae false \
  -i inventory/demo.yml \
  -e @secrets.yml \
  -e cloudflare_zone=entrenchedrealist.dev
```

Each host's FQDN comes from its inventory entry; its public IP comes from
its inventory `ansible_host`. No per-run extra-vars per host.

### From system ansible

```bash
export CLOUDFLARE_API_TOKEN='cf-token-here'

ansible-playbook -i inventory/demo.yml demo_host_init.yml \
  -e cloudflare_zone=entrenchedrealist.dev \
  -e ansible_password="$WIN_ADMIN_PASSWORD"
```

### Production cert vs. staging

Default is **Let's Encrypt staging** so you can re-run freely (untrusted cert,
browser warns, no rate limits worth caring about). For a real trusted cert:

```bash
  -e acme_env=production
```

Production limits: 5 duplicate certs/week, 5 failed validations/hour, 50
certs/week per registered domain. The role is idempotent — re-running within
`cert_remaining_days` (default 30) of an existing cert's expiry does **not**
issue a new cert. `-e cert_remaining_days=999` forces re-issue (the parameter means "cert must have at least N days left"; LE max lifetime is 90).

---

## What `demo_host_init.yml` does

A thin orchestrator over four roles under `roles/` (the parent `ansible.cfg`
sets `roles_path = ./roles`):

| Role | Where it runs | What it does |
|------|---------------|--------------|
| [`demo_prep`](roles/demo_prep/README.md) | localhost (delegated, per-host) | Builds `hello.war` once at `files/hello.war`; upserts each host's Cloudflare A record `<cert_fqdn>` → `<ansible_host>`. |
| [`tomcat_windows_install`](roles/tomcat_windows_install/README.md) | Windows host | Installs Temurin JDK (sets `JAVA_HOME`); silent-installs Tomcat `10.1.x` (service `Tomcat10`); replaces `webapps/ROOT` with `hello.war`. |
| [`letsencrypt_cloudflare`](roles/letsencrypt_cloudflare/README.md) | delegated to localhost | Runs the ACME order; writes `_acme-challenge` TXT records via Cloudflare; pauses for DNS propagation; tells ACME to validate; retrieves cert/chain/fullchain to `.acme/`. TXT records are cleaned up in an `always` block. |
| [`tomcat_windows_tls`](roles/tomcat_windows_tls/README.md) | Windows host (cert build delegated to localhost) | Builds `<fqdn>.p12`; ships it to `conf/`; templates `server.xml` (HTTP `:8080`, TLS `:8443` → the keystore); restarts Tomcat (gated on actual change); verifies the cert on `:8443` and that the hello app responds. |

Each role has its own README documenting its variables and assumptions.

---

## Demoing the renewal

`renew_tomcat_cert.yml` reuses the last two roles (`letsencrypt_cloudflare`
+ `tomcat_windows_tls`) and adds a pre-flight check that reads the live cert
from the Tomcat connector. If it's > `cert_remaining_days` from expiry, the
play ends early — no LE order, no restart. Otherwise it re-issues, ships, and
restarts in one job.

```bash
ansible-navigator run renew_tomcat_cert.yml \
  --eei quay.io/truch/tomcat-windows-cert-renewal:1.1 \
  --pull-policy missing \
  --mode stdout \
  --pae false \
  -i inventory/demo.yml \
  -e @secrets.yml \
  -e cloudflare_zone=entrenchedrealist.dev
```

To force a fresh issuance (e.g. to demo what a real renewal looks like):

```bash
  -e cert_remaining_days=999
```

---

## Teardown

Terminate the EC2 instance and delete the A record in the Cloudflare dashboard
(or re-run `community.general.cloudflare_dns` with `state: absent`). Locally,
clean up:

```bash
rm -rf .acme files/*.p12 files/hello.war
```

---

## Notes / gotchas

- **Cloudflare token scope** — give the token only `Zone:Zone:Read` +
  `Zone:DNS:Edit` for the one zone you're using. A broader token would still
  work but breaks least-privilege.
- **Java not found after Tomcat install** — sometimes the machine environment
  needs a reboot to expose `JAVA_HOME`. The play fails fast; reboot and re-run.
- **Tomcat version aging out** — `dlcdn.apache.org` only hosts current
  releases. Bump `tomcat_version` if `10.1.55` returns 404, or point
  `tomcat_installer_url` at `archive.apache.org`.
- **Files that should never be committed:** `.acme/`, `files/*.p12`,
  `files/hello.war`, `secrets.yml`. The repo `.gitignore` covers all of these.
