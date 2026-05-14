# Tomcat on Windows Certificate Renewal

Renews an SSL certificate on Apache Tomcat running as a Windows service. Ships
a renewed PKCS12 keystore, updates the SSL Connector in `server.xml` to point
at it, restarts the Tomcat service, and verifies the live cert on the SSL port.

## Important: Tomcat requires a restart

Unlike Apache `httpd` (graceful reload) or IIS (rebind by thumbprint), Tomcat
does **not** hot-reload SSL configuration. The connector picks up the new
keystore only on service restart. Schedule a maintenance window or take the
node out of the load balancer rotation before running this play.

## What it does

1. Backs up `server.xml` to `server.xml.bak_<date>`.
2. Copies the renewed `.p12` into the Tomcat `conf/` directory with a
   date-versioned filename and grants the Tomcat service account read access.
3. Edits the `Connector` element in `server.xml` via `community.windows.win_xml`
   — updating only the `certificateKeystoreFile`, `certificateKeystorePassword`,
   and `certificateKeystoreType` attributes on the matching SSLHostConfig
   Certificate. The rest of `server.xml` is left untouched.
4. Restarts the Tomcat Windows service.
5. Waits for the SSL connector to come back up, then fetches the live cert
   from the control node and prints the renewed subject + expiry.

## Rollback

The previous `.p12` is still on disk; `server.xml.bak_<date>` is the
pre-change config. Roll back by restoring the backup and restarting:

```yaml
- ansible.windows.win_copy:
    src: 'C:\...\server.xml.bak_2026-04-11'
    dest: 'C:\...\server.xml'
    remote_src: true
- ansible.windows.win_service:
    name: Tomcat10
    state: restarted
```

## Tomcat version compatibility

The XPath in the playbook targets the **Tomcat 8.5+** connector schema:

```xml
<Connector port="8443">
  <SSLHostConfig>
    <Certificate certificateKeystoreFile="..."
                 certificateKeystorePassword="..."
                 certificateKeystoreType="PKCS12"/>
  </SSLHostConfig>
</Connector>
```

If you're on Tomcat 7 / older 8.0 using the legacy connector style:

```xml
<Connector port="8443" SSLEnabled="true"
           keystoreFile="..."
           keystorePass="..."
           keystoreType="PKCS12"/>
```

then change the XPath to target the Connector itself and set `keystoreFile`
instead of `certificateKeystoreFile`:

```yaml
xpath: "/Server/Service/Connector[@port='8443']"
attribute: keystoreFile
```

## Layout

```
tomcat_windows/
├── README.md
├── renew_tomcat_cert.yml
├── requirements.yml
├── files/
│   └── wildcard_example_com.p12       # not committed
└── inventory/
    ├── hosts.yml
    └── host_vars/
        └── tomcat-win01.example.com.yml
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

Targeting a different Tomcat install:

```bash
ansible-playbook -i inventory/hosts.yml renew_tomcat_cert.yml \
  -e "tomcat_home=C:\\Program Files\\Apache Software Foundation\\Tomcat 9.0" \
  -e tomcat_service=Tomcat9 \
  -e connector_port=8443
```

## AAP / Controller

Use a **Machine** credential for WinRM and a **Vault** credential for the
keystore password. For zero-downtime renewals, build a workflow template:

1. Drain node from load balancer
2. Run this play
3. Health-check the node
4. Return node to load balancer
