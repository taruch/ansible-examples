# Tomcat on Linux Certificate Renewal

Renews an SSL certificate on Apache Tomcat running on Linux (systemd-managed).
Ships a renewed PKCS12 keystore, updates the SSL Connector in `server.xml` to
point at it, restarts the Tomcat service, and verifies the live cert on the
SSL port.

## Important: Tomcat requires a restart

Tomcat does **not** hot-reload SSL configuration. The connector picks up the
new keystore only on service restart. Schedule a maintenance window or drain
the node from the load balancer before running this play.

## What it does

1. Validates the renewed `.p12` on the control node and parses it with
   `community.crypto.openssl_pkcs12` to confirm the password is correct
   *before* touching the target.
2. Backs up `server.xml` to `server.xml.bak_<date>`.
3. Copies the renewed `.p12` into the Tomcat `conf/` directory with a
   date-versioned filename, owned by the Tomcat service user.
4. Edits the `Connector` element in `server.xml` via `community.general.xml`
   — updating only the `certificateKeystoreFile`, `certificateKeystorePassword`,
   and `certificateKeystoreType` attributes on the matching SSLHostConfig
   Certificate. The rest of `server.xml` is left untouched.
5. Restarts the Tomcat systemd service.
6. Waits for the SSL connector to come back up, fetches the live cert from
   the control node, and asserts it matches.

## Rollback

The previous `.p12` is still on disk; `server.xml.bak_<date>` is the
pre-change config. Restore and restart:

```bash
cp /opt/tomcat/conf/server.xml.bak_2026-04-11 /opt/tomcat/conf/server.xml
systemctl restart tomcat
```

## Tomcat version compatibility

The XPath targets the **Tomcat 8.5+** connector schema:

```xml
<Connector port="8443">
  <SSLHostConfig>
    <Certificate certificateKeystoreFile="..."
                 certificateKeystorePassword="..."
                 certificateKeystoreType="PKCS12"/>
  </SSLHostConfig>
</Connector>
```

For Tomcat 7 / older 8.0 using the legacy connector style, target the
Connector element directly:

```yaml
xpath: "/Server/Service/Connector[@port='8443']"
attribute: keystoreFile
```

## Distro defaults

The playbook defaults to `/opt/tomcat` and service name `tomcat`. Common
package-managed alternatives:

| Distro / package | `tomcat_home` | service / user |
|------------------|----------------|----------------|
| Manual tarball install | `/opt/tomcat` | `tomcat` |
| RHEL `tomcat` package | `/usr/share/tomcat` | `tomcat` |
| Debian `tomcat9` | `/var/lib/tomcat9` | `tomcat9` |
| Ubuntu `tomcat10` | `/var/lib/tomcat10` | `tomcat10` |

Override in `host_vars/`.

## Layout

```
tomcat_linux/
├── README.md
├── renew_tomcat_cert.yml
├── requirements.yml
├── files/
│   └── wildcard_example_com.p12       # not committed
└── inventory/
    ├── hosts.yml
    └── host_vars/
        └── tomcat-lnx01.example.com.yml
```

## Prerequisites

```bash
ansible-galaxy collection install -r requirements.yml
```

Place the renewed PKCS12 keystore under `files/`:

```
files/wildcard_example_com.p12
```

Encrypt the keystore password with ansible-vault (or use an AAP Vault credential):

```bash
ansible-vault encrypt_string 'changeit' --name vault_keystore_password
```

## Usage

```bash
ansible-playbook -i inventory/hosts.yml renew_tomcat_cert.yml --ask-vault-pass
```

Targeting a packaged Tomcat 9 on Debian:

```bash
ansible-playbook -i inventory/hosts.yml renew_tomcat_cert.yml \
  -e tomcat_home=/var/lib/tomcat9 \
  -e tomcat_service=tomcat9 \
  -e tomcat_user=tomcat9 \
  -e tomcat_group=tomcat9
```

## AAP / Controller

Use a **Machine** credential for SSH and a **Vault** credential for the
keystore password. For zero-downtime renewals, build a workflow template:

1. Drain node from load balancer
2. Run this play
3. Health-check the node
4. Return node to load balancer
