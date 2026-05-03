# Restart Services

Playbooks for restarting services on Linux and Windows hosts.

## Playbooks

### `restart_linux_services.yml`
Restarts a list of Linux services (e.g., `sshd`, `nginx`, `apache2`) on target hosts. Detects systemd availability and uses the `systemd` or `service` module accordingly. Ensures each service is enabled to start on boot after restart.

### `restart_windows_services.yml`
Restarts Windows services (e.g., `Spooler`, `BITS`) using the `win_service` module with elevated privileges via `runas`. Displays the result status for each service after restart.

## Usage
Override the default service list via extra variables:

```yaml
# Linux
ansible-playbook restart_linux_services.yml -e "services=['nginx','sshd']"

# Windows
ansible-playbook restart_windows_services.yml -e "win_services=['Spooler']"
```
