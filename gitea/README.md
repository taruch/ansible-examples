# Gitea Deployment

Deploys [Gitea](https://gitea.io/) as a Podman container on RHEL 9/10, fronted by nginx with HTTPS (self-signed cert), with firewalld configuration and systemd persistence.

## Requirements

- RHEL 9 or 10 target host
- `containers.podman` and `ansible.posix` collections installed
- `become` privileges on the target

## Usage

```bash
ansible-playbook gitea.yml -i "<host>," -e "_hosts=<host>" -u <user> --private-key <key>
```

** IMPORTANT! Playbook defaults to `localhost` if `_hosts` is not provided.**

## Variables

| Variable | Default | Description |
|---|---|---|
| `gitea_image` | `ghcr.io/go-gitea/gitea` | Container image |
| `gitea_version` | `latest` | Image tag |
| `gitea_data_dir` | `/var/lib/gitea` | Host path for persistent data |
| `gitea_http_port` | `3000` | Internal Gitea HTTP port (bound to 127.0.0.1 only) |
| `gitea_ssh_port` | `2222` | SSH port (mapped to container port 22) |
| `gitea_ssl_cert` | `/etc/nginx/ssl/gitea.crt` | Path for the self-signed SSL certificate |
| `gitea_ssl_key` | `/etc/nginx/ssl/gitea.key` | Path for the SSL private key |

## What it does

1. Installs Podman, nginx, openssl, firewalld, and supporting packages via dnf
2. Creates data and config directories under `gitea_data_dir`
3. Generates a self-signed SSL certificate (skipped if already present)
4. Configures nginx as a reverse proxy: HTTP on port 80 redirects to HTTPS, port 443 proxies to Gitea
5. Starts firewalld and opens ports 80, 443, and the SSH port
6. Enables the `httpd_can_network_connect` SELinux boolean so nginx can proxy to the container
7. Pulls the Gitea image from GitHub Container Registry
8. Runs the Gitea container (HTTP bound to `127.0.0.1` only — not directly exposed)
9. Generates a systemd unit file via `podman generate systemd` and enables it as `container-gitea`
10. Enables and starts nginx

After deployment, Gitea is accessible at `https://<host>`. Complete initial setup through the web UI on first access. Browsers will show a certificate warning due to the self-signed cert.
