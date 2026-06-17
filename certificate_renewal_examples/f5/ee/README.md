# F5 Certificate Renewal Execution Environment

This directory contains the definition for a container image (Execution
Environment) that bundles all dependencies needed to run F5 BIG-IP certificate
renewal playbooks via Let's Encrypt.

## What's included

- **Base image:** `registry.redhat.io/ansible-automation-platform-25/ee-supported-rhel9:latest`
  - Note: We use `ee-supported` (not `ee-minimal`) because this EE needs to compile Python packages that require build tools
- **Collections:**
  - `f5networks.f5_modules` (>= 1.32.0) — F5 BIG-IP modules
  - `ansible.netcommon` (>= 7.0.0) — Network automation utilities
  - `community.crypto` (>= 2.22.0) — Let's Encrypt ACME, certificate operations
  - `community.general` (>= 10.0.0) — Cloudflare DNS module
- **Python packages:**
  - `cryptography` — Certificate and key generation
  - `requests` — HTTP client for APIs
  - `f5-sdk` — F5 iControl REST SDK
  - `bigsuds` — F5 SOAP API client (legacy)
  - `netaddr` — Network address manipulation
- **System packages:**
  - `python3-devel`, `libffi-devel`, `openssl-devel` — Build deps for cryptography
  - `git` — Ansible Galaxy collection installation

## Building the image

Requires `ansible-builder` (install via `pip install ansible-builder`).

```bash
cd ee
ansible-builder build --tag f5-cert-renewal:1.0 -v3
```

This creates a local image `f5-cert-renewal:1.0`.

## Publishing the image

Tag and push to a container registry:

```bash
# Tag for Quay
podman tag f5-cert-renewal:1.0 quay.io/YOUR_USERNAME/f5-cert-renewal:1.0
podman tag f5-cert-renewal:1.0 quay.io/YOUR_USERNAME/f5-cert-renewal:latest

# Log in to Quay
podman login quay.io

# Push
podman push quay.io/YOUR_USERNAME/f5-cert-renewal:1.0
podman push quay.io/YOUR_USERNAME/f5-cert-renewal:latest
```

Replace `YOUR_USERNAME` with your Quay.io username or organization.

## Using the image

### With ansible-navigator (local execution)

```bash
ansible-navigator run ../renew_f5_cert_v2.yml \
  --eei quay.io/YOUR_USERNAME/f5-cert-renewal:1.0 \
  --pull-policy missing \
  --mode stdout \
  --pae false \
  -i ../inventory/hosts.yml \
  -e @../secrets.yml \
  -e cloudflare_zone=example.com
```

### With AAP / Automation Controller

1. Navigate to **Execution Environments** in the AAP UI
2. Add a new EE with image `quay.io/YOUR_USERNAME/f5-cert-renewal:1.0`
3. Assign it to your F5 certificate renewal job template

The EE is pulled automatically when the job runs.

## Customization

To add additional Python packages or collections:

1. Edit `requirements.yml` (Ansible collections)
2. Edit the `python:` section in `execution-environment.yml` (Python packages)
3. Edit `bindep.txt` (system packages)
4. Rebuild the image

## Versioning

- `1.0` — Initial release (f5_modules 1.32+, community.crypto 2.22+)
- `latest` — Tracks the most recent stable build

Pin to a specific version tag in production to avoid surprise breakage from
`latest` updates.

## Troubleshooting

**Build fails with "/usr/bin/dnf: No such file or directory":**

You're using `ee-minimal-rhel9` which only has `microdnf`. This EE requires
`ee-supported-rhel9` for full package management and build tools. Update
`execution-environment.yml` to use the supported base image.

**"Collection not found" at runtime:**

Check that `requirements.yml` is correctly referenced in
`execution-environment.yml` under `dependencies.galaxy`. Rebuild the image.

**Python import errors (e.g., "No module named 'f5'"):**

Verify the Python package is listed in `execution-environment.yml` under
`dependencies.python`. Rebuild the image.

## Support

For EE build issues, consult:
- [Ansible Builder docs](https://ansible.readthedocs.io/projects/builder/)
- [AAP Execution Environment guide](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/)

For F5 certificate renewal logic issues, see the parent [README_v2.md](../README_v2.md).
