# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

Ansible playbooks for deploying [Gitea](https://gitea.io/) (self-hosted Git service) using Podman on RHEL 9/10, intended as examples within a broader AAP (Ansible Automation Platform) examples repository.

## Running the Playbooks

```bash
# Current playbook — requires _hosts variable
ansible-playbook gitea.yml -e "_hosts=<inventory_group_or_host>"

# Legacy playbook — targets hardcoded host 'ansible-1'
ansible-playbook gitea.yml_orignetwork -i ../inventory
```

The parent repo's inventory is at `/home/truch/Ansible-Repos/ansible-examples/inventory`.

## Architecture

### gitea.yml (current)
Modern, standalone deployment for RHEL 9/10:
- Uses `quay.io/gpils/gitea` (avoids Docker Hub pull limits)
- Installs Podman + `python3-firewall` (required for the `firewalld` module)
- Opens ports 3000 (HTTP) and 2222 (SSH) via firewalld
- Mounts data at `/var/lib/gitea/data` with `:Z` for SELinux relabeling
- Generates a systemd unit via `podman generate systemd` and enables `container-gitea`
- Hosts are passed at runtime via `{{ _hosts }}`

### gitea.yml_orignetwork (legacy)
Integrated deployment for an AAP demo environment:
- Targets `ansible-1`, uses Docker Hub image `gitea/gitea:1.14.2`
- Performs full post-deploy init: database setup, `app.ini` configuration, admin user creation
- Creates a `network-demos-repo` by cloning from GitLab and pushing to local Gitea
- Configures NGINX to proxy `/gitea/` and restarts the AAP controller web service

## Key Dependencies

- `containers.podman` collection (for `podman_image` and `podman_container` modules)
- `python3-firewall` must be present on managed hosts for the `firewalld` module
- RHEL 9/10 with `dnf` (current playbook); `slirp4netns` needed for rootless Podman networking
