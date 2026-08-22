# VMware Examples

Playbooks demonstrating VMware vCenter automation with Ansible: provisioning,
power/lifecycle management, disk resizing, snapshots, guest settings, ESXi/VCSA
patching, and troubleshooting VM lookups across datacenters.

## Collections

Required collections are pinned in `collections/requirements.yml`:
`community.vmware`, `community.general`, `vmware.vmware`, `cloud.vmware_ops`
(the last provides the `provision_vm` role used by `vmware_hotadd.yml` and
`vmware_provision.yml`). Install with:

```bash
ansible-galaxy collection install -r vmware_examples/collections/requirements.yml
```

## Credentials

Most playbooks expect `vcenter_hostname` / `vcenter_username` / `vcenter_password`
to be defined (passed with `-e`, `vars_prompt`, or a `vars_files: [secrets.yml]`
include). `secrets.yml` in this directory is an **example/template** vars file
(placeholder values, no real secrets) showing the variable shape a playbook
expects - copy and fill it in, or vault it, for real use.

A couple of playbooks (`vmware_power.yml`, and both vCenter/VM lookup
playbooks) instead read the standard `VMWARE_HOST` / `VMWARE_USER` /
`VMWARE_PASSWORD` / `VMWARE_VALIDATE_CERTS` environment variables, which AAP
auto-injects when a VMware credential is attached to the job template - pass
`--penv=VMWARE_USER --penv=VMWARE_PASSWORD` etc. when running locally via
ansible-navigator.

## Running against AAP

`setup.yml` only wires up **4 of the playbooks in this directory** into
Ansible Automation Platform: `vmware_provision.yml`, `vmware_power.yml`,
`vmware_hotadd.yml`, and `vmware_snapshots.yml`, as job templates
(`VMWare / Create VM`, `VMWare / VM Power State Change`,
`VMWare / Hot Add CPU - RAM`, `VMWare / Snapshot / Create` and
`/ Delete`), plus a credential, an inventory + VMware inventory source, and
two workflows (`VMWare / Update VM OS`, `VMWare Provision from ServiceNow`).
Everything else in this directory (disk-extend variants, ESXi install,
guest tools, vCenter/VCSA upgrade, and the two vCenter/VM lookup playbooks
below) has **no AAP job template** and is meant to be run via
`ansible-navigator`/`ansible-playbook` directly, or wired up manually if you
want it in AAP.

`setup.yml` also assumes a custom credential type named `VMWare Demo
Credential` already exists in the target AAP organization - it is not
created by this project. If it isn't already present, credential creation
(and everything that depends on it) will fail; create it first or point
`controller_credentials` at a credential type you already have (e.g. the
built-in `VMware vCenter` type).

Run `setup.yml` once via the repo-root `setup_demo.yml`:

```bash
export CONTROLLER_PASSWORD=<changeme>
export CONTROLLER_USERNAME=<changeme>
export CONTROLLER_HOST=<changeme>
export CONTROLLER_VERIFY_SSL=false
ansible-navigator run -mstdout setup_demo.yml \
  --eei=quay.io/ansible-product-demos/apd-ee-25:latest \
  --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD \
  --penv=CONTROLLER_HOST --penv=CONTROLLER_VERIFY_SSL \
  -e demo=vmware_examples
```

## Playbook catalog

### Provisioning

- **`vmware_provision.yml`** - Clones a VM from `vm_template` via the
  `cloud.vmware_ops.provision_vm` role, waits for it to power on and get an
  IP, then reports the VM's facts (and forwards them to a follow-on job via
  `set_stats`). Vars: `vm_name`, `vcenter_folder`, `vm_template`, `vm_cpus`,
  `memsize_MiB` (plus `secrets.yml` for vCenter connection details).
- **`vmware_hotadd.yml`** - Hot-adds CPU/memory to an existing VM via the same
  provisioning role (requires `hotadd_memory`/`hotadd_cpu` enabled on the
  guest). Vars: `vm_name`, `vcenter_folder`, `vm_memory_mb`, `vm_num_cpus`
  (new values must be larger than current or the module errors).
- **`vmware_install_esxi.yml`** - Two-play bare-metal ESXi build: PXE/kickstart
  boot an ESXi host via iDRAC (`dellemc.openmanage`), then wait for it to come
  up and register it into vCenter with `community.vmware.vmware_host`.

### Power management

- **`vmware_power.yml`** - Sets a VM's power state (`on`/`off`/`restart`) via
  `vmware.vmware.vm_powerstate`. By default it leaves `VMWARE_HOST`/`VMWARE_USER`/
  `VMWARE_PASSWORD` exactly as injected by the AAP VMware credential; set
  `vmware_host`/`vmware_user`/`vmware_password` (or `vcenter_hostname`/etc.) as
  extra vars only if you need to override them. Vars: `vm_name`,
  `vmpowerstate`. Datacenter is hardcoded to `SDDC-Datacenter` - edit for your
  environment.

### Disk management

Three independent takes on the same problem (extend a vSphere-level disk,
then grow the guest filesystem to match) - pick the one that fits your
workflow rather than running all three:

- **`vmware_extend_disk.yml`** - Extends a disk by `disk_label`, then (second
  play, targeting the VM by inventory hostname) grows the Linux partition and
  filesystem with `community.general.parted`/`filesystem`. Prompts for
  `vcenter_password` via `vars_prompt`.
- **`vmware_extend_disk fix.yml`** - Standalone version that looks up the
  disk's controller/unit number from `community.vmware.vmware_guest_disk_info`
  first, then resizes by that address instead of by label directly.
- **`extend_disk_ben.yml`** - Datadog-driven variant: pulls the list of hosts
  currently alerting on low disk space from the Datadog API, finds each one in
  vCenter with `vmware_guest_find`, bumps its first disk by 5GB if under
  100GB, then extends the Windows `C:` partition with `win_partition`.

### Snapshots

- **`vmware_snapshots.yml`** - Create or remove-all snapshots for a VM via
  `community.vmware.vmware_guest_snapshot`, gated by tags (`snapshot_create` /
  `snapshot_remove_all`). Vars: `vm_name`, `vcenter_datacenter`,
  `vcenter_folder` (plus `secrets.yml`). Used as the pre/post steps in the
  `VMWare / Update VM OS` AAP workflow.

### Guest settings

- **`vmware_tools.yml`** - Sets a VM's VMware Tools upgrade policy to
  `upgrade_at_power_cycle` via `community.vmware.vmware_guest`. VM name and
  datacenter are hardcoded (`my-vm-01` / `MyDatacenter`) - edit before use.

### Patching / upgrades

- **`vmware_vcenter_upgrade.yml`** - Mounts a VCSA patch ISO via the vCenter
  API, then SSHes into the VCSA appliance itself to stage and install the
  update with `software-packages`, waiting out the reboot. Prompts for both
  the vCenter and VCSA root passwords.

### vCenter / VM lookup & troubleshooting

Credentials for these two come from the AAP VMware credential attached to the
job template (`VMWARE_USER`/`VMWARE_PASSWORD`/`VMWARE_VALIDATE_CERTS`); only
`VMWARE_HOST` is overridden per vCenter. Neither has an AAP job template
defined in `setup.yml` - run them via `ansible-navigator`, or create a job
template manually with a VMware credential attached and a survey for the
vars below.

- **`vmware_vcenter_vm_search.yml`** - Searches every vCenter/datacenter
  pair in the `vsphere_it` list for a VM by exact name, and reports found /
  confirmed-not-found / search-error per datacenter. Fails if the VM isn't
  found anywhere and every datacenter was actually searched.

  ```bash
  ansible-navigator run -mstdout vmware_examples/vmware_vcenter_vm_search.yml \
    -e vm_name=<vm-name> --penv=VMWARE_USER --penv=VMWARE_PASSWORD
  ```

- **`vmware_vcenter_vm_dump.yml`** - Dumps every VM registered in a single
  vCenter/datacenter. Use this when the search playbook reports "not found"
  but you believe the VM is actually there - list everything in the
  datacenter and eyeball/grep it for near-matches (case, trailing characters,
  extra whitespace, wrong datacenter, etc.). Supports an optional
  case-insensitive substring filter, and if nothing matches it prints the
  list of datacenter names it actually saw on that vCenter.

  ```bash
  ansible-navigator run -mstdout vmware_examples/vmware_vcenter_vm_dump.yml \
    -e datacenter=<datacenter-name> -e vc_host=<vcenter-fqdn> \
    [-e vm_name_filter=<substring>] \
    --penv=VMWARE_USER --penv=VMWARE_PASSWORD
  ```

## Other files

- **`secrets.yml`** - Example vars file for `vcenter_hostname`/`vcenter_username`/
  `vcenter_password` and friends; template only, not real credentials.
- **`scratch.txt`**, **`ansible-navigator.log`** - Local scratch/log artifacts,
  not part of any playbook.
