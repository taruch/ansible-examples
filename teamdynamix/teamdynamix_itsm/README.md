# teamdynamix.itsm

Ansible collection for integrating with the [TeamDynamix](https://www.teamdynamix.com/) ITSM REST API.

## Contents

| Type | Name | Description |
|------|------|-------------|
| Inventory plugin | `teamdynamix.itsm.tdx_cmdb` | Dynamic inventory from the TDX CMDB/Asset API |
| Playbook | `teamdynamix.itsm.create_incident` | Create a new incident ticket |
| Playbook | `teamdynamix.itsm.update_incident` | Update fields / add a comment to an existing ticket |

All content uses `ansible.builtin` modules only — no additional collection dependencies.

---

## Installation

```bash
# From this directory (development)
ansible-galaxy collection install .

# Or build and install
ansible-galaxy collection build
ansible-galaxy collection install teamdynamix-itsm-1.0.0.tar.gz
```

---

## Authentication

All plugins and playbooks authenticate with a **TDX Service Account** using BEID + Web Services Key.

To create a service account in TDX:
> Admin → Users → Create User → enable **"Is Service Account"** → copy **BEID** and **Web Services Key**

Grant the service account read access to the Asset application (for CMDB inventory) and
create/edit access to the Ticketing application (for incident management).

---

## Inventory Plugin: `teamdynamix.itsm.tdx_cmdb`

Queries the TDX Asset/CMDB API and returns hosts grouped by **Location** and **Status**.

### Configuration file

Create a file ending in `tdx_cmdb.yml` (or `tdx.yml`):

```yaml
# inventory/tdx_cmdb.yml
plugin: teamdynamix.itsm.tdx_cmdb
instance: myorg          # subdomain: myorg.teamdynamix.com
app_id: 40               # Asset application ID (integer from Admin URL)
beid: "{{ lookup('env', 'TDX_BEID') }}"
wskey: "{{ lookup('env', 'TDX_WS_KEY') }}"

# Optional — filter by asset status (default: "In Use" only)
status_filter:
  - "In Use"
  - "In Maintenance"

# Optional — use a custom attribute ID as ansible_host instead of asset Name
# host_attr_id: 9876
```

### Usage

```bash
export TDX_BEID=<your-beid> TDX_WS_KEY=<your-wskey>

# Inspect inventory
ansible-inventory -i inventory/tdx_cmdb.yml --list
ansible-inventory -i inventory/tdx_cmdb.yml --graph

# Use as inventory source
ansible-playbook site.yml -i inventory/tdx_cmdb.yml
```

### Resulting groups

```
all
├── loc_data_center_east       ← assets at location "Data Center East"
├── loc_remote_office
├── status_in_use              ← assets with status "In Use"
└── status_in_maintenance
```

### Host variables

Each host gets these variables set automatically:

| Variable | Source field |
|----------|-------------|
| `ansible_host` | `host_attr_id` attribute value, or asset Name |
| `tdx_asset_id` | Asset ID |
| `tdx_serial` | SerialNumber |
| `tdx_manufacturer` | ManufacturerName |
| `tdx_model` | ProductModelName |
| `tdx_status` | StatusName |
| `tdx_location` | LocationName |
| `tdx_owner_dept` | OwningDepartmentName |

### In AAP

Add the inventory config YAML as a **Source from a Project** with **Inventory Plugin** type,
or set the environment variables (`TDX_BEID`, `TDX_WS_KEY`, etc.) on the inventory source
using a custom credential type.

---

## Playbook: `teamdynamix.itsm.create_incident`

```bash
ansible-playbook teamdynamix.itsm.create_incident \
  -e tdx_instance=myorg \
  -e tdx_app_id=35 \
  -e tdx_beid=$TDX_BEID \
  -e tdx_wskey=$TDX_WS_KEY \
  -e ticket_type_id=111 \
  -e ticket_account_id=222 \
  -e ticket_status_id=333 \
  -e ticket_priority_id=444 \
  -e "ticket_title='Database server unreachable'" \
  -e "ticket_description='The primary DB host stopped responding at 14:30 UTC.'"
```

Sets the fact `tdx_ticket_id` for use in downstream plays or workflows.

---

## Playbook: `teamdynamix.itsm.update_incident`

```bash
# Update status and add a feed comment
ansible-playbook teamdynamix.itsm.update_incident \
  -e tdx_instance=myorg \
  -e tdx_app_id=35 \
  -e tdx_beid=$TDX_BEID \
  -e tdx_wskey=$TDX_WS_KEY \
  -e tdx_ticket_id=98765 \
  -e update_status_id=555 \
  -e "update_comment='Remediation script applied. Monitoring for recurrence.'"

# Comment only (no field changes)
ansible-playbook teamdynamix.itsm.update_incident \
  -e tdx_instance=myorg \
  -e tdx_app_id=35 \
  -e tdx_beid=$TDX_BEID \
  -e tdx_wskey=$TDX_WS_KEY \
  -e tdx_ticket_id=98765 \
  -e "update_comment='Escalated to DBA team.'"
```

---

## Finding TDX Integer IDs

TypeID, StatusID, PriorityID, and AccountID are org-specific. Retrieve them via the API:

```bash
TOKEN=$(curl -s -X POST \
  https://myorg.teamdynamix.com/TDWebApi/api/auth/loginadmin \
  -H "Content-Type: application/json" \
  -d "{\"BEID\":\"$TDX_BEID\",\"WebServicesKey\":\"$TDX_WS_KEY\"}" | tr -d '"')

# Ticket types
curl -s -H "Authorization: Bearer $TOKEN" \
  https://myorg.teamdynamix.com/TDWebApi/api/35/tickets/types | python3 -m json.tool

# Ticket statuses
curl -s -H "Authorization: Bearer $TOKEN" \
  https://myorg.teamdynamix.com/TDWebApi/api/35/tickets/statuses | python3 -m json.tool

# Priorities
curl -s -H "Authorization: Bearer $TOKEN" \
  https://myorg.teamdynamix.com/TDWebApi/api/35/tickets/priorities | python3 -m json.tool

# Asset custom attributes (to find host_attr_id)
curl -s -H "Authorization: Bearer $TOKEN" \
  https://myorg.teamdynamix.com/TDWebApi/api/attributes/custom?componentId=63 | python3 -m json.tool
```
