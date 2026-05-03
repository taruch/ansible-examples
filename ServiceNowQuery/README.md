# ServiceNow Query

Examples for querying ServiceNow CMDB and APIs from Ansible playbooks.

## Playbooks

### `servicenow_example.yml`
Queries the ServiceNow CMDB (`cmdb_ci_computer` table) for server records using the `servicenow.servicenow` collection. Returns OS field values for matched CIs.

### `SN_example_stage_1.yml` / `SN_example_stage_2.yml` / `SN_example_stage_3.yml`
Multi-stage ServiceNow integration workflow demonstrating progressive query and update patterns (e.g., open incident → update fields → close).

### `uri_example.yml`
Direct ServiceNow REST API interaction using Ansible's `uri` module — useful when the ServiceNow collection is not available or for custom API endpoints.

## Required Variables
| Variable | Description |
|----------|-------------|
| `snow_instance` | ServiceNow instance name (e.g., `dev12345`) |
| `snow_username` | ServiceNow username |
| `snow_password` | ServiceNow password |

## Requirements
- `servicenow.servicenow` collection (for `servicenow_example.yml` and stage playbooks)
- Network access to the ServiceNow instance
