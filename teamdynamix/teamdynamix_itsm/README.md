# teamdynamix.itsm

Ansible collection for integrating with the [TeamDynamix](https://www.teamdynamix.com/) ITSM REST API. The [TDX Web API Explorer](https://api.teamdynamix.com/TDWebApi/) is the canonical reference for all endpoints, field names, and request/response shapes.

## Contents

| Type | Name | Description |
|------|------|-------------|
| Module | `teamdynamix.itsm.incident` | Create / update / delete an incident ticket (idempotent, supports check_mode) |
| Module | `teamdynamix.itsm.incident_info` | Look up a ticket by ID, or search via TDX `/tickets/search` |
| Inventory plugin | `teamdynamix.itsm.tdx_cmdb` | Dynamic inventory from the TDX CMDB/Asset API |
| Playbook | `teamdynamix.itsm.create_incident` | Example: create a ticket using the `incident` module |
| Playbook | `teamdynamix.itsm.update_incident` | Example: read with `incident_info`, update with `incident` |
| Playbook | `teamdynamix.itsm.get_incident_info` | Example: look up a ticket by ID or search by query |

The two modules mirror the pattern used by `servicenow.itsm` (`incident` + `incident_info`), backed by shared `module_utils/` (client, errors, arguments, utils, payload mapping).

---

## Installation

```bash
# From this directory (development)
ansible-galaxy collection install .

# Or build and install
ansible-galaxy collection build
ansible-galaxy collection install teamdynamix-itsm-1.1.0.tar.gz
```

---

## Authentication

The `incident` and `incident_info` modules authenticate with TDX using **either**:

1. **Username + password** — the module POSTs to `/api/auth` and caches the returned bearer token for the duration of the run.
2. **Token** — a bearer token you've already obtained out-of-band; the module uses it directly without calling `/auth`.

The user (or whoever issued the token) needs at minimum *create / edit* access to the Ticketing application. For `requestor`/`responsible` name lookup, *view* access to People is also required.

Connection parameters can be supplied inline or via environment variables:

| Suboption | Env var |
|-----------|---------|
| `host` | `TDX_HOST` |
| `app_id` | `TDX_APP_ID` |
| `username` | `TDX_USERNAME` |
| `password` | `TDX_PASSWORD` |
| `token` | `TDX_TOKEN` |
| `timeout` | `TDX_TIMEOUT` |

The `tdx_cmdb` inventory plugin uses the same auth shape (`username` + `password`, or `token`).

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
username: "{{ lookup('env', 'TDX_USERNAME') }}"
password: "{{ lookup('env', 'TDX_PASSWORD') }}"
# ...or in place of username/password:
# token: "{{ lookup('env', 'TDX_TOKEN') }}"

# Optional — filter by asset status (default: "In Use" only)
status_filter:
  - "In Use"
  - "In Maintenance"

# Optional — use a custom attribute ID as ansible_host instead of asset Name
# host_attr_id: 9876
```

### Usage

```bash
export TDX_USERNAME=<your-username> TDX_PASSWORD=<your-password>
# or:  export TDX_TOKEN=<your-bearer-token>

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
or set the environment variables (`TDX_USERNAME`, `TDX_PASSWORD`, or `TDX_TOKEN`) on the
inventory source using a custom credential type.

---

## Module: `teamdynamix.itsm.incident`

Idempotent ticket CRUD. `state: present` creates a new ticket if `id` is omitted, otherwise updates the ticket with that ID. `state: absent` deletes by `id`. Supports `--check` mode.

```yaml
- name: Create or update a ticket
  teamdynamix.itsm.incident:
    instance:
      host: myorg            # or full URL: https://myorg.teamdynamix.com
      app_id: 35
      username: "{{ lookup('env', 'TDX_USERNAME') }}"
      password: "{{ lookup('env', 'TDX_PASSWORD') }}"
      # ...or in place of username/password:
      # token: "{{ lookup('env', 'TDX_TOKEN') }}"
    state: present
    title: "Database server unreachable"
    description: "Primary DB host stopped responding at 14:30 UTC."
    type_id: <your-type-id>             # tenant-specific ints — see
    account_id: <your-account-id>       # "Finding TDX Integer IDs" below
    status_id: <your-new-status-id>
    priority_id: <your-priority-id>
  register: result

- name: Move ticket to In Progress
  teamdynamix.itsm.incident:
    instance: "{{ tdx_instance }}"
    id: "{{ result.record.id }}"
    status_id: <your-in-progress-status-id>

- name: Open a ticket — resolve users by name, plus extra TDX fields
  teamdynamix.itsm.incident:
    instance: "{{ tdx_instance }}"
    title: "VPN access request"
    type_id: <your-type-id>
    status_id: <your-new-status-id>
    priority_id: <your-priority-id>
    requestor: jdoe@example.com    # username, email, or UID; resolved via /people/search
    responsible: helpdesk-tier1
    other:                          # arbitrary TDX PascalCase fields the module doesn't expose
      Tags: ["vpn", "remote-access"]
      EstimatedHours: 2
```

### Required fields when creating

When `id` is omitted (i.e. creating a new ticket), the module requires the following:

| Field | TDX field | Description |
|-------|-----------|-------------|
| `title` | `Title` | Short summary of the ticket |
| `type_id` | `TypeID` | Ticket type (e.g. *Incident*, *Service Request*) — values are tenant-specific |
| `status_id` | `StatusID` | Initial status (e.g. *New*, *Open*) — values are tenant-specific |
| `priority_id` | `PriorityID` | Priority (e.g. *Low*, *High*) — values are tenant-specific |

Optional but commonly set:

| Field | TDX field | Description |
|-------|-----------|-------------|
| `account_id` | `AccountID` | Department / account that owns the ticket |
| `description` | `Description` | Long-form description |
| `requestor` *or* `requestor_uid` | `RequestorUid` | Person reporting the ticket; defaults to the auth'd user |
| `responsible` *or* `responsible_uid` | `ResponsibleUid` | Person/group assigned to work the ticket |
| `impact_id`, `urgency_id`, `source_id` | matching `*ID` | Categorization fields |
| `location_id`, `location_room_id` | matching `*ID` | Where the issue is occurring |
| `service_id`, `service_offering_id` | matching `*ID` | Service catalog mapping |
| `form_id` | `FormID` | TDX form template applied to the ticket |
| `notify_requestor` | n/a (query param) | Whether TDX emails the requestor on create/update (default `true`) |

`type_id`, `status_id`, `priority_id`, `account_id`, `form_id` etc. are **integer IDs that vary per TDX tenant** — see [Finding TDX Integer IDs](#finding-tdx-integer-ids) for how to retrieve them.

The `requestor` / `responsible` options accept a UID (used as-is), a username, or an email; non-UID values are resolved via TDX `/people/search` and must match exactly one active user. They are mutually exclusive with the corresponding `*_uid` options.

The `other` dict is an escape hatch for fields not exposed as named options — keys are passed through verbatim, so use **TDX PascalCase** field names (e.g. `Tags`, `ExternalID`). Values here win over named options on conflict.

Connection parameters can also come from the environment — see the [Authentication](#authentication) table.

### Host formats

`instance.host` accepts three forms:

| Input | Resolved base URL |
|-------|-------------------|
| `myorg` | `https://myorg.teamdynamix.com/TDWebApi/api` |
| `https://myorg.teamdynamix.com` | `https://myorg.teamdynamix.com/TDWebApi/api` |
| `https://tdx.example.com/sbtdwebapi/api` | used verbatim |

Use the third form when the tenant doesn't live under `*.teamdynamix.com` or its API path isn't `/TDWebApi/api` (sandboxes typically use `/sbtdwebapi/api`).

Returns:
- `record` — the created/updated ticket as a dict (snake_case keys)
- `diff.before` / `diff.after` — useful with `--diff`
- `changed` — false when an update is a no-op (existing fields already match)

---

## Module: `teamdynamix.itsm.incident_info`

Read-only lookup. Returns `records` (always a list).

```yaml
- name: Fetch one ticket by ID
  teamdynamix.itsm.incident_info:
    instance: "{{ tdx_instance }}"
    id: 98765

- name: Search for open high-priority tickets containing "database"
  teamdynamix.itsm.incident_info:
    instance: "{{ tdx_instance }}"
    query:
      status_id: [<your-new-status-id>, <your-in-progress-status-id>]   # auto-wrapped to StatusIDs
      priority_id: <your-priority-id>                                    # scalar → [...] → PriorityIDs
      search_text: database
      max_results: 50

- name: Find tickets opened by a specific user (looked up by email)
  teamdynamix.itsm.incident_info:
    instance: "{{ tdx_instance }}"
    query:
      requestor: jdoe@example.com   # resolved to UID, sent as RequestorUids
      status_id: <your-new-status-id>
      max_results: 25
```

`query` accepts Ansible-friendly snake_case keys that get translated into the TDX `TicketSearch` payload. Recognized keys include:

| Snake_case | TDX field | Notes |
|------------|-----------|-------|
| `search_text`, `max_results`, `classification`, `ticket_id` | `SearchText`, `MaxResults`, `TicketClassification`, `TicketID` | scalar |
| `created_date_from`, `created_date_to`, `modified_date_from`, `modified_date_to` | matching `*Date{From,To}` | scalar |
| `is_on_hold`, `is_assigned` | `IsOnHold`, `IsAssigned` | bool |
| `status_id`, `priority_id`, `urgency_id`, `impact_id`, `type_id`, `account_id`, `source_id`, `location_id`, `location_room_id`, `service_id`, `service_offering_id`, `form_id`, `status_class_id` | corresponding `*IDs` | scalar wrapped to one-element list |
| `requestor_uid`, `responsible_uid` | `RequestorUids`, `ResponsibilityUids` | scalar wrapped |
| `requestor`, `responsible` | `RequestorUids`, `ResponsibilityUids` | username/email looked up via `/people/search`, then wrapped |

Any other key is passed through verbatim, so raw TDX PascalCase still works (e.g. `StatusIDs: [<your-new-status-id>]`). See the TDX Web API `TicketSearch` contract for the full field set.

---

## Playbook: `teamdynamix.itsm.create_incident`

```bash
ansible-playbook teamdynamix.itsm.create_incident \
  -e tdx_instance=myorg \
  -e tdx_app_id=35 \
  -e tdx_username=$TDX_USERNAME \
  -e tdx_password=$TDX_PASSWORD \
  -e "ticket_type_id=<your-type-id>" \
  -e "ticket_account_id=<your-account-id>" \
  -e "ticket_status_id=<your-new-status-id>" \
  -e "ticket_priority_id=<your-priority-id>" \
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
  -e tdx_username=$TDX_USERNAME \
  -e tdx_password=$TDX_PASSWORD \
  -e tdx_ticket_id=98765 \
  -e "update_status_id=<your-in-progress-status-id>" \
  -e "update_comment='Remediation script applied. Monitoring for recurrence.'"

# Comment only (no field changes)
ansible-playbook teamdynamix.itsm.update_incident \
  -e tdx_instance=myorg \
  -e tdx_app_id=35 \
  -e tdx_username=$TDX_USERNAME \
  -e tdx_password=$TDX_PASSWORD \
  -e tdx_ticket_id=98765 \
  -e "update_comment='Escalated to DBA team.'"
```

---

## Playbook: `teamdynamix.itsm.get_incident_info`

Two modes — single-ticket lookup by ID, or a search returning a list of records.

```bash
# By ID
ansible-playbook teamdynamix.itsm.get_incident_info \
  -e tdx_instance=myorg \
  -e tdx_app_id=35 \
  -e tdx_username=$TDX_USERNAME \
  -e tdx_password=$TDX_PASSWORD \
  -e tdx_ticket_id=98765

# By search (snake_case keys; scalar *_id values are auto-wrapped to a list)
ansible-playbook teamdynamix.itsm.get_incident_info \
  -e tdx_instance=myorg \
  -e tdx_app_id=35 \
  -e tdx_username=$TDX_USERNAME \
  -e tdx_password=$TDX_PASSWORD \
  -e '{"search_query": {"status_id": ["<your-new-status-id>", "<your-in-progress-status-id>"], "search_text": "database", "max_results": 20}}'
```

Sets the fact `tdx_records` (full list) and `tdx_first_ticket_id` (when at least one match) for use in downstream tasks.

---

## TeamDynamix API documentation

This collection wraps the [TeamDynamix Web API](https://api.teamdynamix.com/TDWebApi/) — the API Explorer linked above is the canonical reference for every field name, request/response shape, and endpoint listed below.

Endpoints touched by this collection:

| Endpoint | Used by |
|----------|---------|
| `POST /auth` | `incident`, `incident_info`, `tdx_cmdb` (when supplying `username`+`password`) |
| `GET /{appId}/tickets/{id}` | `incident` (fetch for update/delete diff), `incident_info` (lookup by ID) |
| `POST /{appId}/tickets` | `incident` (create) |
| `POST /{appId}/tickets/{id}` | `incident` (update) |
| `DELETE /{appId}/tickets/{id}` | `incident` (delete) |
| `POST /{appId}/tickets/search` | `incident_info` (search via `query:`) |
| `POST /people/search` | `requestor` / `responsible` username/email resolution |
| `POST /{appId}/assets/search` | `tdx_cmdb` inventory plugin |

The `query:` parameter on `incident_info` follows the TDX `TicketSearch` schema — see the **Tickets** section of the API Explorer for the full list of supported filters.

---

## Finding TDX Integer IDs

TypeID, StatusID, PriorityID, AccountID, and the rest of the `*_id` fields are tenant-specific. Two ways to look them up:

### From the TDX Admin UI (TDAdmin)

1. Log in as an admin and open **TDAdmin**.
2. In the **Applications** list, click into your Ticketing application.
3. Use the left-hand sidebar to navigate to the section that matches the field you need:
   - **Types** → values for `type_id`
   - **Statuses** → values for `status_id`
   - **Priorities** → values for `priority_id`
   - **Impacts** / **Urgencies** / **Sources** → `impact_id`, `urgency_id`, `source_id`
   - **Forms** → `form_id`
   - **Accounts**, **Locations**, **Services** etc. live under their own top-level Admin sections

The integer ID is shown either as a column on the list page or in the URL when you open an item for edit (e.g. `…/Admin/TicketingApplications/<appId>/Types/Edit?id=<your-type-id>`).

### From the API

Retrieve them programmatically:

```bash
TOKEN=$(curl -s -X POST \
  https://myorg.teamdynamix.com/TDWebApi/api/auth \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$TDX_USERNAME\",\"password\":\"$TDX_PASSWORD\"}" | tr -d '"')

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
