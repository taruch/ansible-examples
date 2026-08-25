# tomcat_windows_tls

Wires an already-installed Tomcat-on-Windows to a freshly issued certificate: builds the PKCS12 keystore on the control node, ships it to the host, templates `server.xml` with the TLS connector, restarts the service, and verifies HTTPS end-to-end.

Designed to be run after `letsencrypt_cloudflare` (which produces the cert artifacts this role consumes) and `tomcat_windows_install` (which sets up Tomcat and deploys the WAR).

## What it does

1. Builds a PKCS12 keystore on the control node from the cert, key, and chain produced by `letsencrypt_cloudflare`.
2. Copies the `.p12` to `{{ tomcat_home }}\conf\<cert_name>.p12` on the Windows host.
3. Grants the Tomcat service account read access to the keystore (`win_acl`).
4. Templates `server.xml` with HTTP/TLS connectors pointed at the keystore.
5. Restarts the Tomcat service and waits for the TLS connector to come up.
6. Fetches the live cert from `:{{ connector_port }}` and confirms the hello app responds (`validate_certs` is disabled automatically against LE staging).

## Required vars

| Var | Description |
|---|---|
| `cert_fqdn` | FQDN of the cert (also used as the PKCS12 friendly name and for HTTPS verification) |

The role also expects cert artifacts to be present on the control node:
- `cert_key_path`, `cert_path`, `chain_path` (defaults assume `letsencrypt_cloudflare` wrote them under `acme_work_dir`).

## Optional vars

| Var | Default | Description |
|---|---|---|
| `tomcat_home` | `C:\Program Files\Apache Software Foundation\Tomcat 10.1` | Tomcat install path |
| `tomcat_service` | `Tomcat10` | Service to restart |
| `tomcat_user` | `NT SERVICE\\Tomcat10` | Service account that needs read on the keystore |
| `http_port` | `8080` | HTTP connector port |
| `connector_port` | `8443` | TLS connector port (matches `tomcat_windows_install`'s firewall rule) |
| `cert_name` | `cert_fqdn` with dots → underscores | Stem for cert files + keystore filename |
| `keystore_password` | `{{ vault_keystore_password \| default('changeit') }}` | Override with a Vault credential in real use |
| `acme_directory` | LE staging | Used to decide whether `validate_certs` is on during verification |
| `p12_local_path` | `{{ acme_work_dir }}/{{ cert_name }}.p12` | Keystore built on the control node |
| `p12_remote_path` | `{{ tomcat_home }}\conf\{{ cert_name }}.p12` | Where the keystore is shipped on the Windows host |
| `server_xml` | `{{ tomcat_home }}\conf\server.xml` | Path to Tomcat's server.xml on the Windows host |

## Requirements

- `ansible.windows` and `community.crypto` collections (declared in `meta/main.yml`)
- Tomcat already installed on the target (run `tomcat_windows_install` first)
- Cert artifacts already on the control node (run `letsencrypt_cloudflare` first)
- **`connector_port` (default `8443`) open inbound on the host's *cloud*
  security group** (AWS/Azure/etc.), not just the Windows Firewall.
  `tomcat_windows_install` opens the Windows Firewall rule automatically,
  but that only helps once traffic can reach the NIC at all. If the cloud
  security group is closed, this role still succeeds at building the
  keystore, templating `server.xml`, and restarting Tomcat — the failure
  only shows up at the very end, in the two verification tasks below
  (`Fetch the live certificate...` / `Confirm the hello app...`), which run
  from the control node over the public network and time out even though
  Tomcat is up and listening locally.
- The app is served on `:{{ connector_port }}` (`8443` by default), **not**
  bare `:443` — `https://<cert_fqdn>/` will fail even when everything is
  working. Browse to `https://<cert_fqdn>:8443/`.

## Example

```yaml
- hosts: tomcat_windows_demo
  roles:
    - role: tomcat_windows_tls
      vars:
        cert_fqdn: tomcat-demo.example.com
```
