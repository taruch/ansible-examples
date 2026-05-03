# Copy Examples

Demonstrates various file copy patterns in Ansible, including cross-platform (Windows-to-Linux, Windows-to-Windows) transfers and credential testing.

## Playbooks

### `copy_cred_test.yml`
Tests that credentials are correctly passed to a job template by printing the `username`, `password`, and SSH key variables received.

### `copy_from_host.yml`
Copies a file from a remote Windows host to a Linux host. Uses `fetch` to pull the file from Windows, then `copy` to place it on the Linux target.

### `copy_from_host_slurp.yml`
Reads file content from a remote host using the `slurp` module (base64-encoded in-memory transfer, no temporary files).

### `copy_to_localproject.yml`
Copies content to the local Ansible project directory on the controller node.

### `copy_w2l.yml`
Creates a file on a Windows host, fetches it to the Ansible controller, then copies it to a Linux host. Demonstrates multi-platform file transfer with task delegation.

### `copy_w2w.yml`
Copies a file between two Windows hosts using fetch and copy with host delegation.

### `copy_w2w_host.yml`
Variation of Windows-to-Windows copy using direct host targeting.

## Requirements
- WinRM configured on Windows hosts
- Appropriate credentials for both Windows and Linux hosts
