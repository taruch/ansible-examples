# Integer Test

Simple playbook demonstrating integer arithmetic in Ansible, specifically epoch time calculations.

## Playbooks

### `test.yml`
Calculates a future epoch timestamp by adding 20 days (converted to seconds) to the current epoch time using Ansible's `ansible_date_time` facts and Jinja2 arithmetic filters.
