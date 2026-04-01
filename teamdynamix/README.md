# TeamDynamix ITSM Examples

Ansible examples for integrating with the [TeamDynamix](https://www.teamdynamix.com/) ITSM REST API.
All playbooks use `ansible.builtin.uri` — no external collections required.

## Files

| File | Purpose |
|------|---------|
| `create_incident.yml` | Create a new incident ticket |
| `update_incident.yml` | Update fields and/or add a comment to an existing ticket |
| `tdx_cmdb_inventory.py` | Dynamic inventory script — pulls assets from the TDX CMDB |

---

## Authentication

All examples authenticate using a **TDX Service Account** (BEID + Web Services Key).

To create a service account:
> TDX Admin → Users → Create User → check **"Is Service Account"** → copy BEID and Web Services Key

---

## Playbooks

### `create_incident.yml`

Creates a new incident ticket and prints the resulting ticket ID and URL.

```bash
ansible-playbook create_incident.yml \
  -e tdx_instance=myorg \
  -e tdx_app_id=35 \
  -e tdx_beid=<BEID> \
  -e tdx_wskey=<WS_KEY> \
  -e ticket_type_id=111 \
  -e ticket_account_id=222 \
  -e ticket_status_id=333 \
  -e ticket_priority_id=444 \
  -e "ticket_title='Database server unreachable'" \
  -e "ticket_description='The primary DB host has stopped responding since 14:30 UTC.'"
```

### `update_incident.yml`

Fetches an existing ticket, optionally updates Status/Priority, and optionally adds a feed comment.

```bash
# Update status and add a comment
ansible-playbook update_incident.yml \
  -e tdx_instance=myorg \
  -e tdx_app_id=35 \
  -e tdx_beid=<BEID> \
  -e tdx_wskey=<WS_KEY> \
  -e tdx_ticket_id=98765 \
  -e update_status_id=555 \
  -e "update_comment='Remediation script applied. Monitoring for recurrence.'"

# Add comment only (no field changes)
ansible-playbook update_incident.yml \
  -e tdx_instance=myorg \
  -e tdx_app_id=35 \
  -e tdx_beid=<BEID> \
  -e tdx_wskey=<WS_KEY> \
  -e tdx_ticket_id=98765 \
  -e "update_comment='Still investigating — escalated to DBA team.'"
```

---

## Dynamic Inventory (`tdx_cmdb_inventory.py`)

Queries the TDX Asset/CMDB API and returns hosts grouped by **Location** and **Status**.

### Configuration (environment variables)

| Variable | Required | Description |
|----------|----------|-------------|
| `TDX_INSTANCE` | Yes | TDX subdomain (e.g. `myorg`) |
| `TDX_APP_ID` | Yes | Asset application ID (integer) |
| `TDX_BEID` | Yes | Service account BEID |
| `TDX_WS_KEY` | Yes | Service account Web Services Key |
| `TDX_HOST_ATTR_ID` | No | Custom attribute ID holding the hostname/IP. Defaults to using the asset **Name** field. |
| `TDX_STATUS_FILTER` | No | Comma-separated status names to include. Default: `In Use` |

### Usage

```bash
# Test output
export TDX_INSTANCE=myorg TDX_APP_ID=40 TDX_BEID=<BEID> TDX_WS_KEY=<WS_KEY>
./tdx_cmdb_inventory.py --list

# Use as inventory source
ansible-playbook site.yml -i tdx_cmdb_inventory.py

# Include multiple statuses
TDX_STATUS_FILTER="In Use,In Maintenance" ansible-playbook site.yml -i tdx_cmdb_inventory.py
```

### Resulting groups

```
all
├── loc_data_center_east    # assets at "Data Center East"
├── loc_remote_office       # assets at "Remote Office"
├── status_in_use           # assets with status "In Use"
└── status_in_maintenance   # assets with status "In Maintenance"
```

### Host variables set per asset

| Variable | Source |
|----------|--------|
| `ansible_host` | Custom attribute (`TDX_HOST_ATTR_ID`) or asset Name |
| `tdx_asset_id` | TDX internal asset ID |
| `tdx_serial` | Serial number |
| `tdx_manufacturer` | Manufacturer name |
| `tdx_model` | Product model name |
| `tdx_status` | Asset status name |
| `tdx_location` | Location name |
| `tdx_owner_dept` | Owning department name |

### In AAP

Add `tdx_cmdb_inventory.py` as a **Script** inventory source. Set the environment variables
above in the inventory source's **Environment Variables** field (or use a Credential with
an Injector that exports them).

---

## Finding TDX IDs

TypeID, StatusID, PriorityID, AccountID, and attribute IDs are org-specific integers.
Retrieve them via the TDX API browser or Admin UI:

```bash
# List ticket types
curl -s -H "Authorization: Bearer <token>" \
  https://myorg.teamdynamix.com/TDWebApi/api/35/tickets/types

# List ticket statuses
curl -s -H "Authorization: Bearer <token>" \
  https://myorg.teamdynamix.com/TDWebApi/api/35/tickets/statuses

# List priorities
curl -s -H "Authorization: Bearer <token>" \
  https://myorg.teamdynamix.com/TDWebApi/api/35/tickets/priorities
```
