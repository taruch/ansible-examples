# Tomcat on Windows Certificate Renewal

Renews an SSL certificate on Apache Tomcat running as a Windows service.
Designed to run on a schedule (AAP, cron, etc.) and **issue the cert in-band**
via Let's Encrypt — no pre-staged `.p12` file required.

## Architecture (Pattern A — in-band LE issuance)

`renew_tomcat_cert.yml` is a thin orchestrator over two roles:

1. **Pre-flight on the Windows host.** Probe the live TLS connector
   (`{{ cert_fqdn }}:{{ connector_port }}`) and read the cert's expiry. If
   the live cert has more than `cert_remaining_days` left (default `30`),
   the play ends early — no ACME order, no restart. This check is what
   makes the play idempotent in **AAP**, where the project filesystem is
   ephemeral and `.acme/` never persists between job runs.

2. **Issue (or refresh) the cert.** `letsencrypt_cloudflare` runs a DNS-01
   challenge against your Cloudflare zone. The new cert lives only inside
   the EE's ephemeral filesystem.

3. **Ship and rotate.** `tomcat_windows_tls` builds a PKCS12 keystore,
   ships it to `conf/`, re-templates `server.xml`, and restarts Tomcat
   **only if** the keystore or `server.xml` actually changed. (The
   Windows firewall rule for the connector port is opened by
   `tomcat_windows_install` at initial bootstrap.)

Tomcat does not hot-reload SSL config — the restart is unavoidable on a
real renewal — but the play won't restart on no-op runs.

## Schedule it

Point an AAP job template (or any scheduler) at `renew_tomcat_cert.yml`
and run it daily or weekly. Each run:

- Almost always no-ops (live cert is still fresh).
- Becomes a real renewal once the live cert is within
  `cert_remaining_days` of expiry — at which point it issues, ships,
  and restarts in a single job.

No need for a separate "is it time?" check; the play is the check.

## Splitting check from update (for change-control workflows)

If you need a ticketing step (ServiceNow change request, ITSM approval,
notification) **between** the "should we renew?" decision and the actual
renewal, the same logic ships as two playbooks you can chain in an AAP
workflow:

| Playbook | Purpose | LE traffic? | Restarts Tomcat? |
|---|---|---|---|
| [`cert_check.yml`](cert_check.yml) | Probe each host, decide if renewal is needed | No | No |
| [`cert_renew.yml`](cert_renew.yml) | Issue + ship + restart | Yes | Yes (when keystore changes) |
| [`renew_tomcat_cert.yml`](renew_tomcat_cert.yml) | Single-shot wrapper that `import_playbook`s both | Yes (when due) | Yes (when due) |

`cert_check.yml` writes these workflow artifacts via `set_stats`:

| Key | Type | Use |
|---|---|---|
| `renewal_targets` | list | Hosts that need renewal |
| `renewal_targets_csv` | string | Same list, comma-separated — drop into the renewal node's `limit` field |
| `renewal_count` | int | Convenience for conditionals |
| `renewal_needed` | bool | Gate the CR-creation branch on this |

### AAP workflow shape

```
┌──────────────────┐    success    ┌──────────────────────────┐    success    ┌────────────────────────────────────────┐
│ Tomcat Windows / │──(renewal_   ▶│ ServiceNow / Create CR   │──────────────▶│ Tomcat Windows / Renew certs           │
│ Check certs      │   needed)     │ (yours)                  │               │ (no pre-flight)                        │
└──────────────────┘               └──────────────────────────┘               │ limit: {{ renewal_targets_csv }}       │
                                                                              └────────────────────────────────────────┘
```

- **Conditional path on the CR node**: only follow the success branch from
  `Check certs` when `renewal_needed` is true. Build that with a workflow
  approval node or a small "guard" job template that fails when nothing
  needs renewing — AAP doesn't yet have native expression-conditioned
  edges in workflows, so use whichever pattern fits your setup.
- **Limit field on the renewal node**: set to `{{ renewal_targets_csv }}`
  so the renewal only runs against hosts the check identified.
- **CR creation playbook** is whatever you already use for SNOW; the
  upstream artifacts (`renewal_targets`, `renewal_count`) are available
  to it as extra-vars and can populate the CR description.

`setup.yml` declares all three templates (`Check certs`, `Renew certs (no
pre-flight)`, and the single-shot `Renew certificate`) — wire your SNOW
template into a workflow in the AAP UI.

## Rate limits

Let's Encrypt production caps to remember:
- **5 duplicate certs / week** per identical FQDN set
- **5 failed validations / hour** per account+hostname
- **50 certs / week** per registered domain (eTLD+1)

The default `cert_remaining_days: 30` keeps you well clear: a single host
issues ~4 certs/year against production. Iterating against the same FQDN
under production should use `-e acme_env=production -e cert_remaining_days=999`
only when you genuinely want a fresh issuance — and even then only
intentionally. The default `acme_env=staging` gives you effectively
unlimited issuances for development.

## Required vars

| Var | Source | Notes |
|---|---|---|
| `cloudflare_zone` | extra-var / inventory | Zone the cert FQDN lives in |
| `cloudflare_api_token` | env `CLOUDFLARE_API_TOKEN`, extra-var, or AAP credential injector | `Zone:Zone:Read` + `Zone:DNS:Edit`, zone-scoped |
| `ansible_password` | inventory / vault / AAP machine credential | Windows admin password |

## Optional vars (with defaults)

| Var | Default | Purpose |
|---|---|---|
| `cert_fqdn` | `inventory_hostname` | FQDN to issue for. The inventory hostname IS the cert by default. |
| `acme_env` | `staging` | Set to `production` for a real trusted cert. |
| `cert_remaining_days` | `30` | Skip renewal when live cert has more than this many days left. Set to `999` to force re-issue (the semantics are "cert must have at least N days left"; `0` means "never renew"). |
| `vault_keystore_password` | `changeit` | Keystore passphrase. Override via AAP Vault credential. |
| `connector_port` | `8443` | Tomcat TLS connector. |
| `tomcat_home` | `C:\Program Files\Apache Software Foundation\Tomcat 10.1` | Install path. |
| `tomcat_service` | `Tomcat10` | Windows service name. |

## Layout

```
tomcat_windows/
├── README.md                       # this file — production renewal flow
├── DEMO.md                         # demo bootstrap walkthrough
├── renew_tomcat_cert.yml           # Pattern A orchestrator (LE issuance + ship)
├── demo_host_init.yml              # initial bootstrap: prep + install + LE + tls
├── requirements.yml                # only used when running with system ansible
├── ansible.cfg                     # roles_path = ./roles
├── secrets.yml                     # gitignored — Cloudflare token + Windows password
├── inventory/
│   ├── hosts.yml                   # production-style inventory (Kerberos, etc.)
│   └── demo.yml                    # demo-style inventory (CredSSP, untrusted WinRM cert)
├── files/                          # gitignored — generated artifacts (hello.war, *.p12)
├── ee/                             # Execution Environment definition
└── roles/
    ├── demo_prep/                  # localhost: hello.war + Cloudflare A record
    ├── tomcat_windows_install/     # Windows: install Java + Tomcat
    ├── letsencrypt_cloudflare/     # localhost: ACME DNS-01 via Cloudflare
    └── tomcat_windows_tls/         # Windows: build .p12, ship, configure, restart
```

## Execution Environment

A pre-built image is published on Quay:

```
quay.io/truch/tomcat-windows-cert-renewal:1.1   # current
quay.io/truch/tomcat-windows-cert-renewal:latest
```

Source for the EE definition lives in [`ee/`](ee/README.md). It bundles the
required collections (`ansible.windows`, `community.windows`,
`community.crypto`, `community.general`), Python deps (`pywinrm[credssp]`,
`cryptography`, `requests`), and is built on
`registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel9:latest`.

To rebuild from source:

```bash
cd ee
ansible-builder build --tag tomcat-windows-cert-renewal:<tag> -v3
```

## Running locally with ansible-navigator

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

`secrets.yml` (gitignored) holds the Cloudflare token + Windows admin
password. Each host's public IP lives in `inventory/demo.yml` as
`ansible_host`. The play targets the `tomcat_windows_demo` group; for
production hosts, point at `inventory/hosts.yml` and adjust the play's
`hosts:` line (or rename the group there) to match.

Defaults to LE staging. For a real trusted cert add `-e acme_env=production`.

## AAP / Controller

The fastest path is the configuration-as-code file shipped with this
example: [`setup.yml`](setup.yml). It defines the credential type, the
Cloudflare credential, the EE, the project, the inventory + hosts + group,
the two job templates, and a daily schedule. Apply it via
`../../controller_setup/configure_aap.yml` (which runs
`infra.aap_configuration.dispatch`):

```bash
ansible-navigator run ../../controller_setup/configure_aap.yml \
  -e aap_hostname=aap.example.com \
  -e aap_username=admin \
  -e aap_password='...' \
  -e aap_validate_certs=true
```

You then only need to:

1. Create a **Machine credential** for the Windows hosts (username
   `Administrator`, password). `setup.yml` references it by name via the
   `windows_machine_credential` tunable at the top of the file — set that
   to whatever you named your credential.
2. Open the **Cloudflare** credential in AAP and paste the actual API
   token (it's left blank in the import).
3. (Optional) **Vault credential** for `vault_keystore_password` if you
   want something other than the default `changeit`.

What `setup.yml` creates:

- A custom credential type `Cloudflare API Token` that injects both
  `CLOUDFLARE_API_TOKEN` (env) and `cloudflare_api_token` (extra-var)
- An execution environment pointing at the Quay image
- A git project at `https://github.com/taruch/ansible-examples.git`
- An inventory `Tomcat Windows Demo` with hosts under
  `tomcat_windows_demo`
- Two job templates: `Tomcat Windows / Bootstrap demo host` and
  `Tomcat Windows / Renew certificate`
- A daily schedule on the renewal template (cheap since the pre-flight
  no-ops when certs are fresh)

### Workflow for zero-downtime production renewals

When a renewal is due, Tomcat restarts. For HA deployments wrap the play
in a workflow template:

1. Drain node from load balancer
2. Run `renew_tomcat_cert.yml`
3. Health-check the node
4. Return node to load balancer

## Rollback

If a renewal goes bad and you need to revert, the previous keystore is
still on disk (the play writes `conf/<cert>.p12` and overwrites on next
renewal; the *previous* `.p12` is whatever existed before this run, kept
under the same filename only if the next run hasn't happened yet). For
real rollback safety in production, take a `conf/` snapshot before the
workflow drains the node and restore that snapshot on failure.

## Demo environment

To exercise this against a real host, `demo_host_init.yml` provisions one
end-to-end (Tomcat 10.1, hello.war, initial LE cert). You bring a Windows EC2
instance and a Cloudflare-managed zone; everything else is automated. See
[`DEMO.md`](DEMO.md). The same `renew_tomcat_cert.yml` then runs against the
demo host to exercise the renewal flow.
