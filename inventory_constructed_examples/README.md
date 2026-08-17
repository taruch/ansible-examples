# Constructed Inventory Examples

Create dynamic groups in Ansible Automation Platform based on facts gathered from your hosts. Constructed inventories let you automatically organize hosts by OS, version, hardware specs, domain membership, network vendor, and more — without maintaining static group assignments.

## How It Works

Constructed inventories are a two-step process:

1. **Gather facts** — Run a fact-gathering playbook with **fact caching enabled** on the job template. This stores host facts in AAP's fact cache.
2. **Sync the constructed source** — A constructed inventory source reads the cached facts and builds groups automatically based on the rules you define.

```
┌──────────────────────┐     ┌─────────────────┐     ┌────────────────────────┐
│  gather_facts_*.yml  │────>│  AAP Fact Cache  │────>│  constructed_*.yml     │
│  (job template)      │     │  (per host)      │     │  (inventory source)    │
└──────────────────────┘     └─────────────────┘     └────────────────────────┘
                                                              │
                                                              ▼
                                                     ┌────────────────────┐
                                                     │  Dynamic Groups    │
                                                     │  os_linux          │
                                                     │  distro_rhel       │
                                                     │  rhel_9            │
                                                     │  windows_2022      │
                                                     │  cisco_ios         │
                                                     │  ...               │
                                                     └────────────────────┘
```

## Files

### Fact-Gathering Playbooks

Run these first to populate the fact cache. Each playbook gathers standard facts and sets additional cacheable facts used by the constructed sources.

| Playbook | Target | Key Facts Cached |
|----------|--------|------------------|
| `gather_facts_linux.yml` | Linux hosts | Distribution, version, SELinux, package manager, vCPUs, RAM, virtualization type |
| `gather_facts_windows.yml` | Windows hosts | OS version/build, domain membership, domain role, vCPUs, RAM, timezone, PowerShell version |
| `gather_facts_network.yml` | Network devices | Network OS, model, firmware version, serial number, interface count, connection type |

### Constructed Inventory Sources

Add these as inventory sources in AAP (Source = "Sourced from a Project"). They define the group rules that run against the cached facts.

| Source File | Target | Groups Created |
|-------------|--------|----------------|
| `constructed_linux.yml` | Linux hosts | `os_linux`, `os_redhat`, `os_debian`, `distro_rhel`, `rhel_8`, `rhel_9`, `selinux_enforcing`, `pkg_dnf`, `systemd`, `virtual`, `physical`, `small_linux`, `large_linux`, and more |
| `constructed_windows.yml` | Windows hosts | `os_windows`, `windows_server`, `windows_2019`, `windows_2022`, `domain_joined`, `workgroup`, `domain_controller`, `member_server`, `small_windows`, `large_windows`, and more |
| `constructed_network.yml` | Network devices | `network_devices`, `cisco_ios`, `cisco_nxos`, `arista_eos`, `juniper_junos`, `switches`, `routers`, `firewalls`, `conn_network_cli`, `conn_httpapi`, and more |
| `constructed_combined.yml` | All device types | Combines the key groups from all three into a single source for mixed inventories |

## AAP Setup

### Step 1: Create Job Templates for Fact Gathering

Create a job template for each device type:

| Field | Value |
|-------|-------|
| **Name** | e.g. `CONSTRUCTED / Gather Facts - Linux` |
| **Inventory** | Your target inventory |
| **Project** | The project containing this repo |
| **Playbook** | `constructed_inventory_examples/gather_facts_linux.yml` |
| **Credentials** | Machine credential for target hosts |
| **Use Fact Cache** | **Checked** (this is required) |

Repeat for `gather_facts_windows.yml` and `gather_facts_network.yml` with appropriate credentials.

### Step 2: Add Constructed Inventory Source

On your inventory in AAP:

1. Go to **Sources** tab
2. Click **Add**
3. Configure:

| Field | Value |
|-------|-------|
| **Name** | e.g. `Constructed - Linux Groups` |
| **Source** | Sourced from a Project |
| **Project** | The project containing this repo |
| **Inventory file** | `constructed_inventory_examples/constructed_linux.yml` |
| **Update on launch** | Checked (optional — syncs groups before each job) |

4. Click **Save**, then **Sync**

### Step 3: Run and Verify

1. Run the fact-gathering job template to populate the cache
2. Sync the constructed inventory source
3. Check the **Groups** tab on your inventory — you should see the dynamic groups with hosts assigned

### Scheduling (Recommended)

Schedule the fact-gathering job templates to run periodically (e.g. daily or weekly) so group memberships stay current as hosts change. Set **Update on launch** on the constructed source to rebuild groups automatically before jobs run.

## Groups Reference

### Linux Groups

| Group | Criteria |
|-------|----------|
| `os_linux` | Any non-Windows, non-macOS host |
| `os_redhat` | `ansible_os_family == "RedHat"` |
| `os_debian` | `ansible_os_family == "Debian"` |
| `distro_rhel` | `ansible_distribution == "RedHat"` |
| `distro_ubuntu` | `ansible_distribution == "Ubuntu"` |
| `distro_amazon` | `ansible_distribution == "Amazon"` |
| `distro_rocky` | `ansible_distribution == "Rocky"` |
| `rhel_8`, `rhel_9` | RHEL by major version |
| `ubuntu_22`, `ubuntu_24` | Ubuntu by major version |
| `pkg_dnf`, `pkg_yum`, `pkg_apt` | Package manager |
| `selinux_enforcing` | SELinux in enforcing mode |
| `selinux_disabled` | SELinux disabled |
| `systemd` | Uses systemd init |
| `virtual` | Guest VM |
| `physical` | Bare metal |
| `small_linux` | <= 2 vCPUs and <= 4GB RAM |
| `medium_linux` | 3-8 vCPUs |
| `large_linux` | > 8 vCPUs |

Additionally, `keyed_groups` create groups dynamically: `distro_RedHat`, `distro_Ubuntu`, `arch_x86_64`, `virt_kvm`, etc.

### Windows Groups

| Group | Criteria |
|-------|----------|
| `os_windows` | `ansible_os_family == "Windows"` |
| `windows_server` | Server product type |
| `windows_workstation` | Non-server product type |
| `windows_2016` | Build 14393.x |
| `windows_2019` | Build 17763.x |
| `windows_2022` | Build 20348.x |
| `windows_2025` | Build 26100.x |
| `domain_joined` | Host is joined to an AD domain |
| `workgroup` | Host is not domain-joined |
| `domain_controller` | Domain controller role |
| `member_server` | Member server role |
| `small_windows` | <= 2 vCPUs and <= 4GB RAM |
| `medium_windows` | 3-8 vCPUs |
| `large_windows` | > 8 vCPUs |

Additionally, `keyed_groups` create groups by domain name (`domain_EXAMPLE`), timezone (`tz_Eastern_Standard_Time`), and domain role.

### Network Groups

| Group | Criteria |
|-------|----------|
| `network_devices` | `ansible_network_os` is defined |
| `cisco_ios` | IOS devices (excludes NXOS) |
| `cisco_nxos` | Nexus OS devices |
| `arista_eos` | Arista EOS devices |
| `juniper_junos` | Juniper JunOS devices |
| `vyos` | VyOS devices |
| `paloalto` | Palo Alto PAN-OS devices |
| `switches` | Model string contains switch/catalyst/nexus |
| `routers` | Model string contains router/ISR/ASR/CSR |
| `firewalls` | Model string contains firewall/ASA/PA- |
| `conn_network_cli` | Uses CLI connection |
| `conn_httpapi` | Uses HTTP API connection |
| `conn_netconf` | Uses NETCONF connection |

Additionally, `keyed_groups` create groups by network OS, firmware version, and model.

## Usage Examples

Once the groups are built, use them in your playbooks:

```yaml
# Patch all RHEL 9 hosts
- hosts: rhel_9
  tasks:
    - ansible.builtin.dnf:
        name: "*"
        state: latest

# Configure all domain controllers
- hosts: domain_controller
  tasks:
    - ansible.windows.win_feature:
        name: RSAT-AD-Tools
        state: present

# Upgrade firmware on all Cisco IOS switches
- hosts: cisco_ios:&switches
  tasks:
    - cisco.ios.ios_command:
        commands: show version

# Target large Linux VMs only
- hosts: large_linux:&virtual
  tasks:
    - ansible.builtin.debug:
        msg: "Large VM: {{ inventory_hostname }}"
```

## Collections Required

| Device Type | Collections |
|-------------|-------------|
| Linux | (none — uses built-in modules) |
| Windows | `ansible.windows` |
| Cisco IOS | `cisco.ios` |
| Cisco NXOS | `cisco.nxos` |
| Arista EOS | `arista.eos` |
| Juniper JunOS | `junipernetworks.junos` |
| VyOS | `vyos.vyos` |

```bash
ansible-galaxy collection install ansible.windows cisco.ios cisco.nxos arista.eos junipernetworks.junos vyos.vyos
```

## Tips

- **Fact cache must be populated first.** The constructed source only reads cached facts — if no facts are cached for a host, it won't be added to any groups.
- **Use `strict: false`** in the constructed source so that missing facts don't cause errors (hosts without a particular fact are simply skipped for that group).
- **Schedule fact gathering** to keep groups current. Host OS upgrades, new domain joins, and hardware changes won't be reflected until facts are re-gathered.
- **Use the combined source** (`constructed_combined.yml`) if you have a single mixed inventory rather than separate inventories per device type.
- **Add your own groups** by editing the `groups:` or `keyed_groups:` sections in the constructed source files. Any fact in the cache can be used as a grouping criterion.
