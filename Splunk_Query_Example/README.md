# Splunk Query Example

Query a Splunk instance for log entries related to a specific host using the Splunk REST API. No extra Ansible collection is required — all API calls are made with `ansible.builtin.uri`.

## Use Case

A rulebook activation detects an open ServiceNow incident for a host. It triggers the **SPLUNK / Enrich ServiceNow Incident from Rulebook** workflow, which:

1. Runs `splunk_query.yml` to query Splunk for recent log entries related to the host
2. Passes the results downstream via `set_stats`
3. Runs `enrich_incident.yml` to append a formatted log summary to the incident's work notes

## Playbooks

### `splunk_query.yml`
Submits a Splunk search job, polls until complete, then retrieves and displays the results. Runs on `localhost` (the AAP execution node) and queries Splunk over its REST API (default port 8089).

The playbook outputs results line by line (`timestamp | host | source | raw_event`) and passes the full result set to follow-on playbooks via `set_stats`.

### `enrich_incident.yml`
Receives Splunk results from an upstream workflow node (via `set_stats`) and appends a formatted log summary to the work notes of a ServiceNow incident. Requires the `servicenow.itsm` collection.

## Required Variables

### `splunk_query.yml`

| Variable | Description | Default |
|---|---|---|
| `splunk_host` | Hostname or IP of the Splunk instance | _(from credential)_ |
| `splunk_port` | Splunk REST API port | `8089` |
| `splunk_username` | Splunk username | _(from credential)_ |
| `splunk_password` | Splunk password | _(from credential)_ |
| `splunk_token` | Bearer token (alternative to username/password) | _(from credential)_ |
| `search_host` | Hostname to search logs for (as it appears in Splunk) | _(survey)_ |
| `search_index` | Splunk index to search | `*` |
| `search_earliest` | Splunk time modifier for the start of the search window | `-24h` |
| `search_latest` | End of the search window | `now` |
| `result_count` | Maximum number of results to return | `50` |
| `splunk_validate_certs` | Validate Splunk TLS certificate | `false` |

### `enrich_incident.yml`

| Variable | Description | Source |
|---|---|---|
| `snow_incident_number` | ServiceNow incident to update (e.g. `INC0010001`) | survey |
| `snow_instance` | ServiceNow hostname | credential |
| `snow_username` | ServiceNow username | credential |
| `snow_password` | ServiceNow password | credential |
| `splunk_results` | Log entries from the Splunk query | `set_stats` (upstream job) |
| `splunk_result_count` | Number of results returned | `set_stats` (upstream job) |
| `splunk_search_host` | Host that was queried | `set_stats` (upstream job) |

## Authentication

The playbook supports two authentication methods, both configured via the **Splunk** credential type:

- **Basic auth** — provide `splunk_username` and `splunk_password`; leave `splunk_token` blank
- **Token auth** — provide `splunk_token` (Bearer token); leave username/password blank

## `set_stats` Output

The playbook exports the following for use by downstream jobs in a workflow:

| Variable | Description |
|---|---|
| `splunk_results` | Full list of result objects from Splunk |
| `splunk_result_count` | Number of results returned |
| `splunk_search_host` | The hostname that was queried |

## Adding to Ansible Automation Platform

Run `setup.yml` from the root of the repo to create the credential types, credentials, job templates, and workflow:

```bash
export CONTROLLER_PASSWORD=<changeme>
export CONTROLLER_USERNAME=<changeme>
export CONTROLLER_HOST=<changeme>
export CONTROLLER_VERIFY_SSL=false
ansible-navigator run -mstdout setup_demo.yml --eei=quay.io/ansible-product-demos/apd-ee-25:latest \
  --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD --penv=CONTROLLER_HOST --penv=CONTROLLER_VERIFY_SSL \
  -e demo=Splunk_Query_Example
```

This creates:
- **Splunk** custom credential type (with `splunk_host`, `splunk_port`, `splunk_username`, `splunk_password`, `splunk_token` fields)
- **Splunk Demo Credential** — pre-populated with `splunk.example.com`; update with your actual values
- **ServiceNow** custom credential type (with `snow_instance`, `snow_username`, `snow_password` fields)
- **ServiceNow Demo Credential** — pre-populated with `mycompany.service-now.com`; update with your actual values
- **SPLUNK / Query Logs for Host** — job template with survey for `search_host`, `search_index`, `search_earliest`, and `result_count`
- **SPLUNK / Enrich ServiceNow Incident** — job template with survey for `snow_incident_number`
- **SPLUNK / Enrich ServiceNow Incident from Rulebook** — workflow that chains the two job templates; survey prompts for `search_host` and `snow_incident_number`

## Requirements

- Network access from the AAP execution node to the Splunk REST API (default port 8089)
- Splunk user account with the `search` capability, or a valid API token
- `servicenow.itsm` collection installed on the execution environment (required for `enrich_incident.yml`)
- ServiceNow user account with write access to incident work notes
