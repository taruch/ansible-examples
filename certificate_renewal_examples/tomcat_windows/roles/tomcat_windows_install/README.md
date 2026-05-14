# tomcat_windows_install

Installs Temurin JDK and Apache Tomcat as a Windows service, then deploys a WAR file as the ROOT webapp.

## What it does

1. Downloads and installs Temurin JDK (sets `JAVA_HOME`).
2. Fails fast if `JAVA_HOME` isn't set after install (sometimes needs a reboot).
3. Downloads and silently installs Tomcat — creates the `Tomcat10` Windows service.
4. Removes the stock `webapps/ROOT` and deploys `{{ war_path }}` as `ROOT.war`.

The TLS connector is **not** configured here — see the `tomcat_windows_tls` role for the cert/keystore/server.xml wiring.

## Variables

| Var | Default | Description |
|---|---|---|
| `java_msi_url` | Temurin 21 LTS installer URL | Override to pin a specific JDK build |
| `tomcat_version` | `10.1.55` | Bump if the version ages out of `dlcdn.apache.org` |
| `tomcat_installer_url` | Apache CDN URL templated from `tomcat_version` | Point at `archive.apache.org` for older versions |
| `tomcat_home` | `C:\Program Files\Apache Software Foundation\Tomcat 10.1` | Install path used by all Tomcat roles |
| `tomcat_service` | `Tomcat10` | Windows service name created by the installer |
| `war_path` | `{{ playbook_dir }}/files/hello.war` | WAR file on the control node, built by `demo_prep` |

## Requirements

- Target host running Windows Server with WinRM configured
- `ansible.windows` collection (declared in `meta/main.yml`)
- WAR file already present on the control node at `war_path`

## Example

```yaml
- hosts: tomcat_windows_demo
  roles:
    - role: tomcat_windows_install
```
