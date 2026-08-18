# Dynamic Network Device Grouping

This example demonstrates how to use constructed inventories to create dynamic, combinable groups for network devices based on vendor, model, function, site, and building — enabling reusable automation that can target any combination of attributes.

## The Problem

Without dynamic grouping, you end up maintaining separate playbooks or static groups for every combination:
- "Alcatel edge switches in Rose Hill Building A"
- "All switches at Lincoln Center"
- "All OS6900 routers everywhere"

This doesn't scale. Every new site, model, or function multiplies the number of groups to maintain.

## The Solution

Define five host variables on each device, and let a constructed inventory source build all the groups automatically:

| Variable | Example | Groups Created |
|----------|---------|----------------|
| `device_vendor` | `alcatel` | `vendor_alcatel`, `alcatel` |
| `device_model` | `OS6860E-P48` | `model_OS6860E_P48`, `alcatel_OS6860E_P48` |
| `device_function` | `edge_switch` | `func_edge_switch`, `edge_switches`, `all_switches` |
| `device_site` | `rose_hill` | `site_rose_hill`, `campus_devices` |
| `device_building` | `building_a` | `bldg_building_a`, `campus_rose_hill_building_a` |

Then combine groups using Ansible's intersection pattern (`:&`) to target exactly what you need:

```
vendor_alcatel:&model_OS6860E_P48:&func_edge_switch:&site_rose_hill:&bldg_building_a
```

## Files

| File | Purpose |
|------|---------|
| `constructed_network_devices.yml` | Constructed inventory source — add to AAP as an inventory source |
| `inventory_example.yml` | Sample inventory showing how to define host variables |
| `example_playbooks.yml` | Playbook examples demonstrating group combinations |

## Targeting Examples

| Target | Host Pattern |
|--------|-------------|
| Alcatel OS6860E-P48 edge switches in Rose Hill Bldg A | `vendor_alcatel:&model_OS6860E_P48:&func_edge_switch:&site_rose_hill:&bldg_building_a` |
| All edge switches at Rose Hill (any vendor) | `edge_switches:&site_rose_hill` |
| All Alcatel switches across all sites | `alcatel:&all_switches` |
| All building routers everywhere | `all_routers` |
| Everything in Rose Hill Building B | `campus_rose_hill_building_b` |
| All data center devices | `datacenter` |
| All OS6900-X20 devices everywhere | `model_OS6900_X20` |
| All firewalls | `firewalls` |
| Extreme devices at Rose Hill | `vendor_extreme:&site_rose_hill` |
| All campus (non-DC) devices | `campus_devices` |

## Host Variable Reference

Set these variables on each host in your AAP inventory:

### `device_vendor` (required)
The device manufacturer in lowercase.

| Value | Description |
|-------|-------------|
| `alcatel` | Alcatel-Lucent Enterprise |
| `extreme` | Extreme Networks |
| `paloalto` | Palo Alto Networks |

### `device_model` (required)
The hardware model. Use the vendor's model designation.

| Value | Description |
|-------|-------------|
| `OS6900-X20` | Alcatel core switch/router |
| `OS6860-P48` | Alcatel aggregation switch |
| `OS6860E-P48` | Alcatel enhanced aggregation/edge switch |
| `OS6850-P24` | Alcatel legacy edge switch |
| `X460-G2-48p` | Extreme edge switch |
| `PA-850` | Palo Alto firewall |

### `device_function` (required)
The network role this device performs. Use these standard values:

| Value | Full Name | Description |
|-------|-----------|-------------|
| `mdr` | Building Router | MDR — campus building router |
| `mds` | Main Aggregation Switch | MDS — primary aggregation layer |
| `mas` | Secondary Aggregation Switch | MAS — secondary aggregation layer |
| `edge_switch` | Edge Switch | Access layer switch |
| `firewall` | Firewall | Security appliance |
| `dc_mdr` | Data Center MDR | Data center router |
| `dc_mds` | Data Center MDS | Data center aggregation switch |
| `dc_edge_switch` | Data Center Edge Switch | Data center access switch |

### `device_site` (required)
The physical site in lowercase with underscores.

| Value | Description |
|-------|-------------|
| `rose_hill` | Rose Hill campus |
| `lincoln_center` | Lincoln Center campus |
| `data_center` | Data center facility |

### `device_building` (required)
The building within a site.

| Value | Description |
|-------|-------------|
| `building_a` | Building A |
| `building_b` | Building B |
| `building_c` | Building C |
| `dc_main` | Main data center floor |

### `device_campus` (optional)
Combined site + building key for single-group targeting. Format: `{site}_{building}`.

Example: `rose_hill_building_a`

## AAP Setup

### Step 1: Set Host Variables

On each host in your AAP inventory, set the five variables (`device_vendor`, `device_model`, `device_function`, `device_site`, `device_building`). You can do this:

- **Manually** in the AAP UI (Host → Variables tab)
- **Via a CMDB inventory source** that maps CMDB fields to these variable names
- **Via a playbook** that reads device info and updates AAP host variables using the `ansible.controller.host` module

### Step 2: Add Constructed Inventory Source

1. Navigate to your inventory → **Sources** tab
2. Click **Add**
3. Set:
   - **Name**: `Dynamic Network Device Groups`
   - **Source**: Sourced from a Project
   - **Project**: *(your project containing this repo)*
   - **Inventory file**: `inventory_constructed_examples/network_device_grouping/constructed_network_devices.yml`
   - **Update on launch**: Checked
4. **Save** and **Sync**

### Step 3: Create Reusable Job Templates

Create a single job template per automation task (e.g. "Network / Firmware Upgrade", "Network / Config Backup"). Use an AAP survey to prompt for the target:

| Field | Value |
|-------|-------|
| **Limit** | `{{ _hosts }}` |
| **Survey Variable** | `_hosts` — text field where the operator enters the group pattern |

The operator enters patterns like `edge_switches:&site_rose_hill` at launch time, and the same playbook works for any combination.

## Adding New Sites, Vendors, or Models

No changes to the constructed source are needed. Just:

1. Add the new hosts to your AAP inventory
2. Set the standard host variables on them
3. Sync the constructed inventory source

New groups appear automatically. For example, adding a host with `device_vendor: cisco` automatically creates the `vendor_cisco` group.

To add new **functions** to the convenience groups (`all_switches`, `all_routers`, etc.), update the `groups:` section in `constructed_network_devices.yml`.
