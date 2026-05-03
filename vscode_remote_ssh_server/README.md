# VS Code Remote SSH Server Setup

Sets up a remote Linux host as a VS Code Remote SSH development environment with Ansible tooling pre-installed.

## Playbooks

### `setup_vscode_remote.yml`
Configures a RHEL/CentOS host for remote Ansible development:

1. Enables the CodeReady Builder (CRB) repository
2. Installs EPEL
3. Installs system packages: `openssh-server`, `git`, `python3`, `podman`
4. Installs Ansible development tools globally via `pipx`:
   - `ansible-core`
   - `ansible-navigator`
   - `ansible-builder`
   - `ansible-lint`
   - `ansible-dev-tools`
5. Configures `pipx` environment variables so tools are available system-wide

## Requirements
- RHEL 8/9 or compatible target
- `become: true` (root access required)
- Internet access for package installation

## Post-Setup
Connect from VS Code using the **Remote - SSH** extension. The host will have all standard Ansible development tools available in the PATH.
