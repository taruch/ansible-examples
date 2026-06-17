# f5_demo_configure

Configures a newly-provisioned F5 BIG-IP instance with demo objects and issues
an initial Let's Encrypt certificate.

## What it does

1. Provisions LTM module (verifies it's enabled)
2. Sets BIG-IP hostname to match cert FQDN
3. Creates demo pool with httpbin.org as backend
4. Creates client-SSL profile (placeholder cert initially)
5. Creates HTTPS virtual server (port 443)
6. Creates HTTP virtual server (port 80)
7. Issues initial Let's Encrypt certificate via `letsencrypt_cloudflare` role
8. Imports cert to BIG-IP via `f5_tls` role
9. Updates SSL profile to use the new cert
10. Verifies HTTPS connectivity

## Requirements

- **F5 BIG-IP** already provisioned and accessible
- **BIG-IP management IP** and credentials
- **Cloudflare** API token
- **Collections:**
  - `f5networks.f5_modules`
  - `community.crypto`
  - `community.general`

## Role Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `bigip_mgmt_ip` | Yes | - | BIG-IP management IP |
| `bigip_private_ip` | Yes | - | BIG-IP private IP (for VS destination) |
| `f5_admin_user` | Yes | `admin` | BIG-IP admin username |
| `f5_admin_password` | Yes | - | BIG-IP admin password |
| `cert_fqdn` | Yes | - | FQDN for cert |
| `cert_name` | Yes | - | Cert name (underscores, e.g., `bigip_demo_example_com`) |
| `cloudflare_zone` | Yes | - | Cloudflare DNS zone |
| `cloudflare_api_token` | Yes | - | Cloudflare API token |
| `acme_env` | No | `staging` | `staging` or `production` |
| `demo_backend_host` | No | `httpbin.org` | Pool member backend |
| `partition` | No | `Common` | BIG-IP partition |

## BIG-IP Objects Created

| Type | Name | Purpose |
|------|------|---------|
| Pool | `demo_pool` | Backend pool with HTTP monitor |
| Pool Member | `httpbin.org:80` | Demo backend (or custom via `demo_backend_host`) |
| Client-SSL Profile | `clientssl_{{ cert_name }}` | Holds the Let's Encrypt cert |
| Virtual Server | `demo_vs_https` | HTTPS listener (443) |
| Virtual Server | `demo_vs_http` | HTTP listener (80) |
| SSL Certificate | `{{ cert_name }}_{{ date }}.crt` | Versioned cert object |
| SSL Key | `{{ cert_name }}_{{ date }}.key` | Versioned key object |
| SSL Chain | `{{ cert_name }}_{{ date }}_chain.crt` | Intermediate chain |

## Example Playbook

```yaml
- hosts: localhost
  roles:
    - role: f5_demo_configure
      vars:
        bigip_mgmt_ip: 10.1.1.100
        bigip_private_ip: 10.0.1.50
        f5_admin_password: MyPassword123!
        cert_fqdn: bigip-demo.example.com
        cert_name: bigip_demo_example_com
        cloudflare_zone: example.com
        cloudflare_api_token: "{{ cloudflare_token }}"
        acme_env: staging
```

## Backend Pool Member

By default, the pool uses `httpbin.org:80` as a backend for demo purposes. This
is an external public service, so it requires the BIG-IP to have internet access.

To use a custom backend:

```yaml
demo_backend_host: 192.168.1.10
demo_backend_port: 8080
```

For a real demo, deploy a simple web server in the same VPC and point the pool
member at it.

## Certificate Validation

With `acme_env=staging` (default), the cert is issued by Let's Encrypt staging
CA. Browsers will show a certificate warning. This is expected — staging certs
are for testing only.

Switch to `acme_env=production` for a real trusted cert.

## Verification

The role attempts to verify HTTPS connectivity at the end:

```yaml
- ansible.builtin.uri:
    url: "https://{{ cert_fqdn }}"
    validate_certs: false  # when using staging
```

If this fails, check:
- DNS propagation (A record points to BIG-IP public IP)
- Security group allows 443/tcp inbound
- Virtual server is enabled
- Backend pool member is reachable from BIG-IP

## Dependencies

This role includes two other roles:
- `letsencrypt_cloudflare` - Issues the cert
- `f5_tls` - Imports cert to BIG-IP

Make sure those roles are available in the `roles/` directory.

## License

MIT

## Author

Todd Ruch
