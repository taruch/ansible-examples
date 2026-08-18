# Inventory Targeting Examples

Complex host targeting patterns for Ansible and AAP. These examples build on the group structure created by constructed inventories (see `inventory_constructed_examples/`) and demonstrate how to dynamically select hosts at runtime using Jinja2 templating, host patterns, AAP surveys, and rolling strategies.

## The Problem

Constructed inventories solve the **grouping** problem — automatically organizing hosts by OS, vendor, site, role, etc. But you still need to **combine** those groups at launch time:

- "Patch all RHEL 9 hosts in production, excluding domain controllers"
- "Upgrade firmware on Alcatel edge switches at Westpark Building A"
- "Roll out a config change to 25% of switches at a time, canary-style"

Static playbooks with hardcoded `hosts:` lines don't scale. You'd need a separate playbook for every combination.

## The Solution

Use **dynamic targeting** — the `hosts:` field is evaluated at runtime using Jinja2 and survey variables, so a single playbook can target any combination of groups.

```
┌─────────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  AAP Survey         │────>│  Jinja2 in hosts:    │────>│  Host Pattern    │
│                     │     │                      │     │                  │
│  vendor: alcatel    │     │  {% set pattern %}   │     │  vendor_alcatel  │
│  role: edge_switch  │     │  pattern.append()    │     │  :&role_edge_sw  │
│  site: westpark     │     │  join(':&')          │     │  :&site_westpk   │
│  building: all      │     │  {% endset %}        │     │                  │
└─────────────────────┘     └─────────────────────┘     └──────────────────┘
```

## Files

| File | Description |
|------|-------------|
| `setup.yml` | **Configuration as Code** — creates constructed inventory sources, fact-gathering templates, targeting job templates (with surveys), and a workflow in AAP via `infra.aap_configuration.dispatch` (uses an existing project) |
| `multi_attribute_targeting.yml` | Jinja2 dynamic `hosts:` with 4-attribute intersection (vendor, role, site, building) |
| `multi_attribute_targeting_os.yml` | Same pattern for OS-based targeting (os, distro, version, env, size) |
| `rolling_update.yml` | Survey-driven rolling update with selectable strategy (fixed, canary, percentage), batch size, and failure threshold |
| `pattern_examples.yml` | Reference for all host pattern syntax: intersection (`&`), union (`:`), exclusion (`!`), regex (`~`), wildcard (`*`) |
| `survey_driven_targeting.yml` | Six AAP survey patterns: free-text, single-select, two-dropdown, comma list, exclusion, multi-select |
| `rolling_and_batch_targeting.yml` | Rolling update reference examples with `serial`, canary deployments, failure thresholds, host ordering |
| `conditional_targeting.yml` | Runtime `group_by`, `when` conditions, dynamic includes, delegation |
| `aap_survey_spec.json` | AAP survey definition for `multi_attribute_targeting.yml` — import directly into a job template |

## How Multi-Attribute Dynamic Targeting Works

The core technique uses Jinja2 in the `hosts:` field to build an intersection pattern from survey variables:

```yaml
hosts: >-
  {%- set pattern = [] -%}
  {%- if target_vendor != 'all' %}{% set _ = pattern.append('vendor_' ~ target_vendor) %}{% endif -%}
  {%- if target_role != 'all' %}{% set _ = pattern.append('role_' ~ target_role) %}{% endif -%}
  {%- if target_site != 'all' %}{% set _ = pattern.append('site_' ~ target_site) %}{% endif -%}
  {%- if target_building != 'all' %}{% set _ = pattern.append('building_' ~ target_building) %}{% endif -%}
  {{ pattern | join(':&') if pattern else 'all' }}
```

Each survey variable maps to a constructed inventory group. When set to `all`, that attribute is skipped — no filter is applied for that dimension. The remaining selections are joined with `:&` (intersection), so only hosts in ALL selected groups are targeted.

### Example Resolutions

| Survey Selections | Resolved Pattern |
|-------------------|-----------------|
| vendor=alcatel, role=edge_switch, site=westpark, building=building_a | `vendor_alcatel:&role_edge_switch:&site_westpark:&building_building_a` |
| vendor=alcatel, role=all, site=westpark, building=all | `vendor_alcatel:&site_westpark` |
| vendor=all, role=all, site=all, building=all | `all` |
| vendor=all, role=firewall, site=all, building=all | `role_firewall` |

## Host Pattern Quick Reference

| Pattern | Meaning | Example |
|---------|---------|---------|
| `group1` | All hosts in group1 | `os_linux` |
| `group1:group2` | Union — hosts in group1 OR group2 | `distro_rhel:distro_ubuntu` |
| `group1:&group2` | Intersection — hosts in group1 AND group2 | `rhel_9:&env_production` |
| `group1:!group2` | Exclusion — hosts in group1 but NOT group2 | `os_linux:!env_production` |
| `~regex` | Regex match on hostname | `~wp-a-.*` |
| `host*` | Wildcard match | `wp-a-*` |
| `host1,host2` | Explicit host list | `web01,web02,web03` |

Patterns chain left to right: `os_linux:&env_production:!large_linux` means "Linux AND production, excluding large instances."

## AAP Setup

### Option A: Configuration as Code (Recommended)

`setup.yml` defines everything as data for `infra.aap_configuration.dispatch`. One command creates the inventory sources, job templates, surveys, and workflow.

**1. Edit tunables** at the top of `setup.yml`:

```yaml
machine_credential: "Demo Credential"      # must already exist in AAP
network_credential: "Network Credential"    # must already exist in AAP
target_organization: "Default"
target_inventory: "Demo Inventory"          # must already exist in AAP
target_project: "Ansible Examples"          # must already exist in AAP
```

**2. Apply** using the shared dispatcher playbook:

```bash
ansible-navigator run -mstdout ../controller_setup/configure_aap.yml \
  -e @inventory_targeting_examples/setup.yml \
  --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD --penv=CONTROLLER_HOST
```

Or include it from any wrapper that calls `infra.aap_configuration.dispatch`:

```yaml
- name: Include targeting configuration
  ansible.builtin.include_vars: inventory_targeting_examples/setup.yml
```

**3. What gets created:**

| Type | Name | Purpose |
|------|------|---------|
| Inventory Source | `Constructed / Combined Groups` | OS, distro, sizing groups from facts |
| Inventory Source | `Constructed / Network Device Groups` | Vendor, model, site, building groups |
| Job Template | `CONSTRUCTED / Gather Facts - Linux` | Populates fact cache (fact cache enabled) |
| Job Template | `CONSTRUCTED / Gather Facts - Windows` | Populates fact cache (fact cache enabled) |
| Job Template | `CONSTRUCTED / Gather Facts - Network` | Populates fact cache (fact cache enabled) |
| Job Template | `TARGETING / Multi-Attribute Network` | 4 dropdown survey (vendor, role, site, building) |
| Job Template | `TARGETING / Multi-Attribute OS` | 5 dropdown survey (os, distro, version, env, size) |
| Job Template | `TARGETING / Rolling Update` | 4 dropdown survey (target group, batch size, strategy, max fail %) |
| Workflow | `TARGETING / Refresh Dynamic Groups` | Runs all 3 fact-gathering templates in parallel |

All survey fields use single-select dropdowns (`multiplechoice`) — operators select from predefined values, no free-text input required.

**4. Initial run:**

1. Launch the **TARGETING / Refresh Dynamic Groups** workflow to populate the fact cache and build groups
2. Launch any **TARGETING/** job template — the survey dropdowns drive the host pattern

Schedule the workflow to run periodically (daily or weekly) to keep groups current.

### Option B: Manual Setup

If you prefer to create the job templates manually in the AAP UI:

1. Set up the constructed inventory sources from `inventory_constructed_examples/` first
2. Create a job template pointing to `multi_attribute_targeting.yml`
3. Import the survey from `aap_survey_spec.json` (or create the four dropdown fields manually)
4. Each field maps to a survey variable (`target_vendor`, `target_role`, `target_site`, `target_building`)
5. Launch — operators select from the survey dropdowns and the Jinja2 in `hosts:` builds the correct intersection pattern automatically

## Rolling Update Strategies

| Strategy | `serial` Value | Use Case |
|----------|---------------|----------|
| Fixed batch | `5` | Predictable batch size |
| Percentage | `"25%"` | Scales with inventory size |
| Canary | `[1, 5, "100%"]` | Test on 1 host, then 5, then all remaining |
| Survey-controlled | `"{{ rollout_serial }}"` | Operator picks batch size at launch |

Combine with `max_fail_percentage` to abort if too many hosts fail:

```yaml
serial: 5
max_fail_percentage: 20   # Abort if >20% of a batch fails
```

## Choosing the Right Approach

| Need | Approach | File |
|------|----------|------|
| Deploy all templates and surveys to AAP automatically | Configuration as Code | `setup.yml` |
| Operator selects from dropdowns, each dimension is optional | Multi-attribute Jinja2 | `multi_attribute_targeting.yml` |
| Operator types any host pattern | Free-text survey | `survey_driven_targeting.yml` (Pattern 1) |
| Two-level filtering (platform + environment) | Two-dropdown intersection | `survey_driven_targeting.yml` (Pattern 3) |
| Target a group but exclude a subset | Group with exclusion | `survey_driven_targeting.yml` (Pattern 5) |
| Controlled rollout with selectable strategy and batch size | Survey-driven rolling update | `rolling_update.yml` |
| Filter by facts gathered at runtime | group_by / when conditions | `conditional_targeting.yml` |
| Static, well-known group combinations | Direct host patterns | `pattern_examples.yml` |
| Reference for serial, canary, ordering options | Rolling update examples | `rolling_and_batch_targeting.yml` |

## Prerequisites

- Constructed inventory groups must be synced before these playbooks run
- AAP survey variables must match the variable names used in the playbooks
- For `multi_attribute_targeting.yml`: groups follow `vendor_*`, `role_*`, `site_*`, `building_*` naming
- For `multi_attribute_targeting_os.yml`: groups follow `os_*`, `distro_*`, `env_*` naming
