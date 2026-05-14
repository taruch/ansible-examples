# Apache (httpd) Certificate Renewal

Renews an Apache SSL certificate by writing **versioned** cert files alongside
the old ones and pointing the vhost config at the new paths. Reload is a
`service reload` (graceful) so in-flight connections aren't dropped.

## What it does

1. Validates the new cert/key files on the control node and reads cert
   metadata with `community.crypto.x509_certificate_info`.
2. Ships the new cert/key/chain with a date-versioned filename
   (e.g. `wildcard_example_com_2026-05-11.crt`) into the standard cert/key
   directories.
3. Renders the vhost config from a template — the cert paths are variables, so
   pointing at the renewed material is a single templated change.
4. Runs `apachectl -t` to validate config before touching the service.
5. Reloads (not restarts) Apache so existing TLS sessions drain naturally.
6. Connects to `:443` from the control node and asserts the served cert's
   `not_after` matches the renewed cert on disk.

## Rollback

Edit `vhost_conf` (or override `cert_version`) to point back at the prior
filename — the old cert files are still on disk under their previous version
suffix.

```bash
ansible-playbook -i inventory/hosts.yml renew_apache_cert.yml \
  -e cert_version=2026-04-11
```

## Layout

```
apache/
├── README.md
├── renew_apache_cert.yml
├── requirements.yml
├── files/                              # drop renewed cert material here
│   ├── wildcard_example_com.crt
│   ├── wildcard_example_com.key
│   └── wildcard_example_com_chain.crt
├── templates/
│   └── ssl_vhost.conf.j2
└── inventory/
    ├── hosts.yml
    └── host_vars/
        └── web01.example.com.yml
```

## Distro defaults

The playbook defaults to RHEL/CentOS paths and service name. For Debian/Ubuntu,
override in `host_vars`:

```yaml
cert_dir: /etc/ssl/certs
key_dir:  /etc/ssl/private
vhost_conf: /etc/apache2/sites-available/ssl_example_com.conf
apache_service: apache2
apache_user: www-data
```

## Prerequisites

```bash
ansible-galaxy collection install -r requirements.yml
```

Place the renewed cert material under `files/`:

```
files/wildcard_example_com.crt
files/wildcard_example_com.key
files/wildcard_example_com_chain.crt
```

## Usage

```bash
ansible-playbook -i inventory/hosts.yml renew_apache_cert.yml
```

## AAP / Controller

Wrap with a Job Template using a Machine credential for SSH. A surveyed
`cert_name` and `server_name` make the same template reusable across every
vhost you renew.
