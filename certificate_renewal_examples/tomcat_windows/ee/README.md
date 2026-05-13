# Execution Environment — Tomcat-on-Windows cert renewal

Definition for an Ansible Execution Environment that runs the playbooks and roles in this directory tree (`../roles/`, `../demo/setup_demo.yml`, `../renew_tomcat_cert.yml`).

## What's in the image

| Layer | Source |
|---|---|
| Base | `registry.redhat.io/ansible-automation-platform-25/ee-minimal-rhel9:latest` — ships with ansible-core + ansible-runner |
| Collections | `requirements.yml` — `ansible.windows`, `community.windows`, `community.crypto`, `amazon.aws` |
| Python deps | `requirements.txt` — `boto3`, `botocore`, `pywinrm[credssp]`, `cryptography` |
| System packages | `bindep.txt` — `zip` (used by `demo_prep` to build `hello.war`) |

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

## Push to a registry

If you're going to use this from AAP controller, push to a registry the controller can reach:

```bash
podman tag tomcat-windows-cert-renewal:latest \
  registry.example.com/automation/tomcat-windows-cert-renewal:latest
podman push registry.example.com/automation/tomcat-windows-cert-renewal:latest
```

Then register it in AAP as an Execution Environment pointing at that pull spec, with a Container Registry credential if the registry is private.

## Use locally (no AAP)

`ansible-navigator` is the easiest way to run a playbook inside the EE from a workstation:

```bash
ansible-navigator run ../demo/setup_demo.yml \
  --eei tomcat-windows-cert-renewal:latest \
  --pae false \
  -i ../demo/inventory/hosts.yml \
  -e cert_fqdn=tomcat-demo.example.com \
  -e route53_zone=example.com \
  -e instance_public_ip=203.0.113.10 \
  -e ansible_password="$WIN_ADMIN_PASSWORD"
```

`--pae false` disables ansible-navigator's playbook artifact recording (often the cause of file-permission surprises on first run).

## Credential handoff

When you run from an EE you no longer have host-side AWS env vars or kubeconfig — everything has to be passed in:

| Need | How |
|---|---|
| AWS creds for Route 53 | Mount `~/.aws` into the EE (`--eev ~/.aws:/runner/.aws:Z`), or set `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` via `--penv` / extra-vars. In AAP, attach an AWS credential to the job template. |
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
