# Cache Facts

Demonstrates Ansible's fact caching feature using the `cacheable` flag on `set_fact`.

## Playbooks

### `set_fact.yml`
Sets custom facts (`my_fact`, `my_other_fact`) with `cacheable: true` so they persist in the configured fact cache across playbook runs. Shows how to update a cached fact and verify the cached value is accessible in subsequent plays.

## Usage
Requires a fact cache backend configured in `ansible.cfg` (e.g., `jsonfile`, `redis`):

```ini
[defaults]
fact_caching = jsonfile
fact_caching_connection = /tmp/ansible_facts
fact_caching_timeout = 86400
```
