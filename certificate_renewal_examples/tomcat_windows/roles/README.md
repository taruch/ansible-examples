# tomcat_windows roles

Roles that compose the Tomcat-on-Windows demo bootstrap ([`../demo_host_init.yml`](../demo_host_init.yml)) and the in-band renewal play ([`../renew_tomcat_cert.yml`](../renew_tomcat_cert.yml)). Both playbooks share these roles via `../ansible.cfg` (`roles_path = ./roles`).

| Role | Targets | Purpose |
|---|---|---|
| [`demo_prep`](demo_prep/README.md) | localhost | Build the demo WAR + upsert the Cloudflare A record |
| [`tomcat_windows_install`](tomcat_windows_install/README.md) | Windows | Install Temurin JDK + Apache Tomcat as a service, deploy a WAR as ROOT |
| [`letsencrypt_cloudflare`](letsencrypt_cloudflare/README.md) | localhost (delegated) | Acquire a Let's Encrypt cert via ACME DNS-01 against Cloudflare |
| [`tomcat_windows_tls`](tomcat_windows_tls/README.md) | Windows | Build PKCS12 keystore, install on Tomcat, configure server.xml, verify HTTPS |

## Running them as a unit

- [`../demo_host_init.yml`](../demo_host_init.yml) chains all four (initial bootstrap of a demo host).
- [`../renew_tomcat_cert.yml`](../renew_tomcat_cert.yml) chains the last two (`letsencrypt_cloudflare` + `tomcat_windows_tls`) for the in-band renewal flow.

See [`../DEMO.md`](../DEMO.md) for the demo walkthrough and provisioning prerequisites.

## Running one role in isolation

Each role has its own `defaults/main.yml`, `meta/main.yml` (with collection deps), and README documenting required + optional vars. Example — fetch a cert without touching Tomcat:

```yaml
- hosts: localhost
  connection: local
  gather_facts: false
  roles:
    - role: letsencrypt_cloudflare
      vars:
        cloudflare_zone: entrenchedrealist.dev
        cert_fqdn: api.entrenchedrealist.dev
        acme_directory: https://acme-v02.api.letsencrypt.org/directory
```

## roles_path

`../ansible.cfg` sets `roles_path = ./roles` so both playbooks at the parent level resolve role names without explicit paths. If you call these roles from elsewhere, set `ANSIBLE_ROLES_PATH` or your own `ansible.cfg` accordingly.
