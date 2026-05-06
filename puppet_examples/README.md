# Puppet → Ansible Examples

Side-by-side examples showing the same configuration expressed in Puppet and in Ansible. Each `.pp` manifest has a functionally equivalent `.yml` playbook.

## Files

| Puppet | Ansible | What it does |
|---|---|---|
| [fapolicyd_example.pp](fapolicyd_example.pp) | [fapolicyd_example.yml](fapolicyd_example.yml) | Install fapolicyd, manage its config, ensure the service runs, refresh the trust DB on config change |
| [motd.pp](motd.pp) | [motd.yml](motd.yml) | Manage `/etc/motd` content |
| [ssh_security_example.pp](ssh_security_example.pp) | [ssh_security_example.yml](ssh_security_example.yml) | Disable root SSH login, ensure sshd is running |
| [users_groups_example.pp](users_groups_example.pp) | [users_groups_example.yml](users_groups_example.yml) | Create `deploy` group and `app_user` user |
| [webserver_example.pp](webserver_example.pp) | [webserver_example.yml](webserver_example.yml) | Install nginx and ensure it's running |

## Concept mapping

| Puppet | Ansible |
|---|---|
| `package { ... }` | `ansible.builtin.package` |
| `service { ... ensure => running, enable => true }` | `ansible.builtin.service` with `state: started, enabled: true` |
| `file { ... content => ... }` | `ansible.builtin.copy` with `content:` |
| `file_line { ... match => ... }` | `ansible.builtin.lineinfile` with `regexp:` |
| `user { ... }` / `group { ... }` | `ansible.builtin.user` / `ansible.builtin.group` |
| `exec { ... refreshonly => true }` | handler triggered via `notify` |
| `notify => Service[...]` | `notify:` on the task → handler restarts service |
| `require => ...` | task ordering in the playbook |

## Running the playbooks

```bash
ansible-playbook -i <inventory> ssh_security_example.yml
```

Each playbook targets `hosts: all` and uses `become: true`. Adjust the host pattern or run with `--limit` to scope where they apply.
