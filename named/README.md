# Named (BIND DNS)

Installs and configures a BIND DNS server using a community role.

## Playbooks

### `site.yml`
Applies the `bertvv.bind` role to install and configure BIND (`named`) on target hosts. Role variables define zones, records, and server options. Uses `become: true` for privilege escalation.

## Requirements
- `bertvv.bind` role (`ansible-galaxy role install bertvv.bind`)
- RHEL/CentOS or compatible Linux target

## Role Variables
See the [bertvv.bind documentation](https://github.com/bertvv/ansible-role-bind) for the full list of supported variables (zones, forwarders, ACLs, etc.).
