# DNS Lookup

Demonstrates DNS resolution from within Ansible playbooks using the `community.general.dig` lookup plugin.

## Playbooks

### `site.yml`
Performs DNS A record and TXT record lookups for multiple domains (`example.org`, `example.com`, `gmail.com`) and displays the results. Useful as a reference for using DNS data in dynamic inventory, conditional logic, or validation tasks.

## Requirements
- `community.general` collection
- `python-dns` (dnspython) installed on the Ansible controller
