# Podman

Playbooks for managing Podman containers, primarily used as a Molecule driver for testing Ansible roles in containers.

## Playbooks

### `create.yml`
Creates Podman containers and networks defined in inventory. Creates the `molecule-linux-test` network, launches containers from the inventory list, and asserts that all containers are in a running state.

### `prepare.yml`
Prepares containers after creation — installs prerequisites needed for Ansible to connect and run tasks inside the containers.

### `container_init.yml`
Initializes container configuration (systemd setup, Python, etc.) required for role testing.

### `inventory.yml`
Molecule inventory defining the container instances (image, name, network) used during test runs.

## Usage
Typically invoked via Molecule rather than directly:

```bash
molecule test
```
