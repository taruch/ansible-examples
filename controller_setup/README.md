# Controller Setup

Playbooks for post-install configuration of Ansible Automation Platform (AAP) Controller.

## Playbooks

### `configure_aap.yml`
Main post-install configuration playbook. Loads variables from `setup.yml` and dispatches the full AAP configuration using the `infra.aap_configuration.dispatch` role, applying organizations, credential types, and other defined resources.

### `create_schedule.yml`
Creates a Job Template schedule in AAP using the `ansible.controller` collection. Configures an RRULE-based recurring schedule (example: daily at 2 AM) with extra variables passed to the scheduled job.

### `setup.yml`
Variable definitions file (sourced by `configure_aap.yml`). Defines AAP organizations and custom credential types such as Dynatrace and ServiceNow, including their input field schemas and injector mappings.

## Requirements
- `infra.aap_configuration` collection
- `ansible.controller` collection
- AAP Controller admin credentials
