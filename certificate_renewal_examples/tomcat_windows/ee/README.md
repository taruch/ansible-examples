# Execution Environment — Tomcat-on-Windows cert renewal

Definition for an Ansible Execution Environment that runs the playbooks and roles in this directory tree (`../roles/`, `../demo_host_init.yml`, `../renew_tomcat_cert.yml`).

## What's in the image

| Layer | Source |
|---|---|
| Base | `registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel9:latest` — ships with ansible-core + ansible-runner, Python 3.11 at `/usr/bin/python3.11` |
| Collections | `requirements.yml` — `ansible.windows`, `community.windows`, `community.crypto`, `community.general` |
| Python deps | `requirements.txt` — `pywinrm[credssp]`, `cryptography`, `requests` |
| System packages | `bindep.txt` — none currently (`demo_prep` builds the WAR with `community.general.archive`, not a shelled-out `zip`) |

DNS work uses `community.general.cloudflare_dns` (already in the `community.general` collection above) — no AWS SDK / boto3 needed.

### Why python_interpreter is pinned to 3.11

The minimal RHEL 9 EE base has Python 3.11 installed at `/usr/bin/python3.11` but the default `/usr/bin/python3` symlink points at the system Python 3.9, which doesn't have `pip`. Without `python_interpreter` in `execution-environment.yml`, the build fails at the pip stage with `No module named pip`. Setting it makes ansible-builder use the correct interpreter.

## Build

You need `ansible-builder >= 3.0` and a container runtime (`podman` or `docker`).

```bash
# Authenticate to registry.redhat.io once with your offline token
podman login registry.redhat.io

cd certificate_renewal_examples/tomcat_windows/ee
ansible-builder build \
  --tag tomcat-windows-cert-renewal:latest \
  --container-runtime podman \
  -v3
```

Build artifacts (the generated `Containerfile`, intermediate context) land in `./context/` by default.

## Pre-built image (public)

A pre-built copy of this EE is published on Quay:

```
quay.io/truch/tomcat-windows-cert-renewal:latest
```

Pull it directly if you don't want to build locally:

```bash
podman pull quay.io/truch/tomcat-windows-cert-renewal:latest
```

In AAP, register it as an Execution Environment with that pull spec — no
credential needed since the repo is public. For your own use, prefer a pinned
tag (e.g. `:2026-05-14`) over `:latest` so controller job runs are reproducible.

## Push to your own registry

To rebuild and publish under a different namespace:

```bash
podman tag tomcat-windows-cert-renewal:latest \
  registry.example.com/automation/tomcat-windows-cert-renewal:latest
podman push registry.example.com/automation/tomcat-windows-cert-renewal:latest
```

Then register it in AAP as an Execution Environment pointing at that pull spec, with a Container Registry credential if the registry is private.

## Use locally (no AAP)

`ansible-navigator` is the easiest way to run a playbook inside the EE from a workstation:

```bash
ansible-navigator run ../demo_host_init.yml \
  --eei quay.io/truch/tomcat-windows-cert-renewal:1.1 \
  --pae false \
  -i ../inventory/demo.yml \
  --penv CLOUDFLARE_API_TOKEN \
  -e @../secrets.yml \
  -e cloudflare_zone=entrenchedrealist.dev
```

`--pae false` disables ansible-navigator's playbook artifact recording (often the cause of file-permission surprises on first run).

## Credential handoff

When you run from an EE you no longer have host-side env vars — everything has to be passed in:

| Need | How |
|---|---|
| Cloudflare API token | `export CLOUDFLARE_API_TOKEN=...` then `--penv CLOUDFLARE_API_TOKEN`, or `-e cloudflare_api_token=...`. In AAP, store as a Vault credential (or a custom Cloudflare credential type) and inject as an env var or extra var. |
| Windows admin password | `-e ansible_password=...` (or AAP Machine credential with username `Administrator`). |
| Keystore passphrase | `-e vault_keystore_password=...` (or AAP Vault credential). |

## Updating the EE

When you change collection or Python deps:

1. Edit `requirements.yml` / `requirements.txt` / `bindep.txt`.
2. Re-run `ansible-builder build` with a new tag (e.g. bump a `:v2` suffix).
3. Push and update AAP to reference the new tag.

Avoid `:latest` for production EEs in AAP — pin to immutable tags so controller jobs are reproducible.

## Notes

- The base image requires a Red Hat subscription at **build** time only; the resulting image runs anywhere.
- `pywinrm[credssp]` is included for broadest WinRM compatibility. If you're using NTLM or Kerberos only, you can drop the `[credssp]` extra to slim the image.
- `cryptography` is what `community.crypto` actually links against — `pyOpenSSL` is no longer required for the modules used here.
