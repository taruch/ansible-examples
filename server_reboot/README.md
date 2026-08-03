# Server Reboot

Playbooks for safely rebooting Linux and Windows servers and confirming they come back online.

## Playbooks

### `linux_server_reboot.yml`
Reboots Linux servers using the `reboot` module. Configures connect and reboot timeouts, waits for the host to become reachable again, then confirms successful reconnection with a debug message.

### `windows_server_reboot.yml`
Reboots Windows servers using the `win_reboot` module over WinRM (NTLM auth, HTTPS). Waits for the host to reconnect after reboot and confirms success.

## AAP Setup

`setup.yml` defines Configuration-as-Code for deploying these playbooks to Ansible Automation Platform 2.6. It creates:

- **SERVER REBOOT / Linux** — job template for `linux_server_reboot.yml`
- **SERVER REBOOT / Windows** — job template for `windows_server_reboot.yml`

Both templates use the Demo Credential and prompt for extra variables and limit at launch.

### Prerequisites

- A Machine credential in AAP (defaults to "Demo Credential")
- An inventory containing the target hosts (defaults to "Demo Inventory")

### Deploying to AAP

```bash
ansible-navigator run -mstdout ../controller_setup/configure_aap.yml \
  -e @setup.yml \
  --penv=CONTROLLER_USERNAME \
  --penv=CONTROLLER_PASSWORD \
  --penv=CONTROLLER_HOST
```

## Usage
Target specific hosts with `--limit` to avoid unintended reboots:

```bash
ansible-playbook linux_server_reboot.yml --limit web_servers
ansible-playbook windows_server_reboot.yml --limit win_servers
```
