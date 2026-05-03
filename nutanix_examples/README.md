# Nutanix Ansible Examples

Ansible playbooks for managing Nutanix AHV VMs via Prism Central. These mirror the functionality of the `vmware_examples` playbooks.

## Prerequisites

- Nutanix Prism Central 2022.x+
- `nutanix.ncp` Ansible collection

Install collections:
```bash
ansible-galaxy collection install -r collections/requirements.yml
```

## Variables

Copy `secrets.yml` and populate with your environment values:

| Variable | Description |
|---|---|
| `nutanix_host` | Prism Central hostname/IP |
| `nutanix_username` | Prism Central username |
| `nutanix_password` | Prism Central password (use Ansible Vault) |
| `nutanix_cluster` | Target AHV cluster name |
| `nutanix_subnet` | Subnet/network name for VM NICs |
| `vm_template` | Disk image name to clone from |
| `cloud_init_script` | _(optional)_ Path to a cloud-init YAML file for guest customization |

## Playbooks

| Playbook | VMware Equivalent | Description |
|---|---|---|
| `nutanix_provision.yml` | `vmware_provision.yml` | Clone a VM from a disk image and power it on |
| `nutanix_power.yml` | `vmware_power.yml` | Change VM power state (on/off/restart) |
| `nutanix_snapshots.yml` | `vmware_snapshots.yml` | Create or delete VM snapshots |
| `nutanix_hotadd.yml` | `vmware_hotadd.yml` | Update vCPU and memory on an existing VM |
| `nutanix_extend_disk.yml` | `vmware_extend_disk.yml` | Extend a VM disk at AHV level + resize OS filesystem |

## Key Differences from VMware

- **Templates**: Nutanix uses disk images rather than VM templates. The `clone_image` parameter references an image in the Image Service.
- **Snapshots**: Nutanix does not have a single "remove all snapshots" call — the snapshot playbook iterates and deletes each one individually.
- **Power state values**: `ON`, `OFF`, `HARD_RESET` (vs VMware's `powered-on`, `powered-off`, `restarted`).
- **VM lookup**: Most Nutanix operations require a VM UUID. The playbooks first query by name via `ntnx_vms_info` to retrieve the UUID before performing updates.
- **Memory units**: Nutanix uses `memory_gb` (vs VMware's `memory_mb`).
- **Disk bus**: AHV uses `SATA` by default (vs VMware's `SCSI`).
- **Network mode**: Networks require `vlan_mode: "ACCESS"` for standard access-mode port groups.
- **Guest customization**: Cloud-init is supported natively via the `guest_customization` block in `ntnx_vms`; supply a `cloud_init_script` path or omit for no customization.
- **Connection defaults**: All playbooks use `module_defaults: group/nutanix.ncp.ntnx:` to define connection parameters once at the play level rather than repeating them in every task.
