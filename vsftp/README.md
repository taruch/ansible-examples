# VSFTP

Restarts the vsftpd FTP server on target hosts.

## Playbooks

### `site.yml`
Restarts the `vsftpd` service using the `systemd` module with `become: true`. Useful as a standalone task or as a handler trigger after configuration changes.
