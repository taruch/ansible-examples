# Gitea Deployment

Deploys [Gitea](https://gitea.io/) as a Podman container on RHEL 9/10, with firewalld configuration and systemd persistence.

## Requirements

- RHEL 9 or 10 target host
- `containers.podman` and `ansible.posix` collections installed
- `become` privileges on the target

## Usage

```bash
ansible-playbook gitea.yml -i "<host>," -e "_hosts=<host>" -u <user> --private-key <key>
```

Defaults to `localhost` if `_hosts` is not provided.

## Variables

| Variable | Default | Description |
|---|---|---|
| `gitea_image` | `ghcr.io/go-gitea/gitea` | Container image |
| `gitea_version` | `latest` | Image tag |
| `gitea_data_dir` | `/var/lib/gitea` | Host path for persistent data |
| `gitea_http_port` | `3000` | HTTP port |
| `gitea_ssh_port` | `2222` | SSH port (mapped to container port 22) |

## What it does

1. Installs Podman, slirp4netns, firewalld, and python3-firewall via dnf
2. Creates data and config directories under `gitea_data_dir`
3. Starts firewalld and opens the HTTP and SSH ports
4. Pulls the Gitea image from GitHub Container Registry
5. Runs the Gitea container with SELinux-compatible volume mount (`:Z`)
6. Generates a systemd unit file via `podman generate systemd` and enables it as `container-gitea`

After deployment, Gitea is accessible at `http://<host>:3000`. Complete initial setup through the web UI on first access.
