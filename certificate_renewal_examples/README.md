# Certificate Renewal Examples

Ansible playbooks for renewing TLS/SSL certificates across common platforms.

Each subdirectory is a self-contained example with its own README, inventory,
and `requirements.yml`.

## Examples

| Directory | Platform | Pattern |
|-----------|----------|---------|
| [`f5/`](./f5/) | F5 BIG-IP LTM | Versioned import + atomic client-SSL profile swap, with UCS backup and rollback |
| [`apache/`](./apache/) | Apache `httpd` / `apache2` | Versioned cert files + templated vhost + `apachectl -t` validation + graceful reload |
| [`iis/`](./iis/) | Microsoft IIS (Windows) | PFX imported into `LocalMachine\My`, site rebound by thumbprint, no service restart |
| [`tomcat_windows/`](./tomcat_windows/) | Apache Tomcat (Windows service) | Versioned `.p12` + targeted `server.xml` edit via `win_xml` + service restart (requires downtime) |
| [`tomcat_linux/`](./tomcat_linux/) | Apache Tomcat (systemd) | Versioned `.p12` + targeted `server.xml` edit via `community.general.xml` + systemd restart (requires downtime) |

## Conventions used across examples

- **Versioned object names** — imports use a date suffix (e.g.
  `wildcard_example_com_2026-05-11`) so the previous cert stays in place and
  rollback is a single task.
- **Pre-change backup** — every playbook snapshots the device or config before
  modifying anything.
- **Atomic cutover** — the profile/binding update is the single moment a client
  sees the new cert; imports and validations happen first.
- **Credentials via env or vault** — examples reference `lookup('env', ...)` so
  they drop cleanly into an AAP credential without code changes.

## Adding a new platform

1. Create a subdirectory (e.g. `netscaler/`, `apache/`, `iis/`).
2. Include a `README.md`, the playbook(s), `requirements.yml`, and a sample
   inventory.
3. Add a row to the table above.
