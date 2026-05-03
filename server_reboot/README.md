# Server Reboot

Playbooks for safely rebooting Linux and Windows servers and confirming they come back online.

## Playbooks

### `linux_server_reboot.yml`
Reboots Linux servers using the `reboot` module. Configures connect and reboot timeouts, waits for the host to become reachable again, then confirms successful reconnection with a debug message.

### `windows_server_reboot.yml`
Reboots Windows servers using the `win_reboot` module over WinRM (NTLM auth, HTTPS). Waits for the host to reconnect after reboot and confirms success.

## Usage
Target specific hosts with `--limit` to avoid unintended reboots:

```bash
ansible-playbook linux_server_reboot.yml --limit web_servers
ansible-playbook windows_server_reboot.yml --limit win_servers
```
