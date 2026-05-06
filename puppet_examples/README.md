# Puppet → Ansible Examples

Side-by-side examples showing the same configuration expressed in Puppet and in Ansible. Each `.pp` manifest has a functionally equivalent `.yml` playbook.

## Resource-level examples

| Puppet | Ansible | What it does |
|---|---|---|
| [fapolicyd_example.pp](fapolicyd_example.pp) | [fapolicyd_example.yml](fapolicyd_example.yml) | Install fapolicyd, manage its config, ensure the service runs, refresh the trust DB on config change |
| [motd.pp](motd.pp) | [motd.yml](motd.yml) | Manage `/etc/motd` content |
| [ssh_security_example.pp](ssh_security_example.pp) | [ssh_security_example.yml](ssh_security_example.yml) | Disable root SSH login, ensure sshd is running |
| [users_groups_example.pp](users_groups_example.pp) | [users_groups_example.yml](users_groups_example.yml) | Create `deploy` group and `app_user` user |
| [webserver_example.pp](webserver_example.pp) | [webserver_example.yml](webserver_example.yml) | Install nginx and ensure it's running |
| [cross_os_webserver.pp](cross_os_webserver.pp) | [cross_os_webserver.yml](cross_os_webserver.yml) | Pick the right Apache package per OS family — `$facts` vs `ansible_facts`, Puppet selectors vs Ansible `when:` |

## Paradigm-shift examples

These cover the conceptual jumps a Puppet user has to make, not just one-for-one resource swaps.

| Example | What it shows |
|---|---|
| [templates_example/](templates_example/) | ERB → Jinja2 — same MOTD rendered both ways, with a syntax mapping table |
| [module_vs_role/](module_vs_role/) | Puppet module → Ansible role — full directory layout side-by-side, variable precedence, invocation patterns |

## Concept mapping

| Puppet | Ansible |
|---|---|
| `package { ... }` | `ansible.builtin.package` |
| `service { ... ensure => running, enable => true }` | `ansible.builtin.service` with `state: started, enabled: true` |
| `file { ... content => ... }` | `ansible.builtin.copy` with `content:` |
| `file { ... content => template(...) }` | `ansible.builtin.template` with `src: file.j2` |
| `file_line { ... match => ... }` | `ansible.builtin.lineinfile` with `regexp:` |
| `user { ... }` / `group { ... }` | `ansible.builtin.user` / `ansible.builtin.group` |
| `exec { ... refreshonly => true }` | handler triggered via `notify` |
| `notify => Service[...]` | `notify:` on the task → handler restarts service |
| `require => ...` | task ordering in the playbook |
| `$facts['os']['family']` | `ansible_facts['os_family']` |
| `case` / selector (`? { ... }`) | `when:` on a task |
| ERB template `<%= @var %>` | Jinja2 template `{{ var }}` |
| Puppet module (`manifests/`, `templates/`, `files/`) | Ansible role (`tasks/`, `templates/`, `files/`, `defaults/`, `handlers/`) |
| Class parameters with defaults | `defaults/main.yml` in a role |
| Hiera | `group_vars/`, `host_vars/`, inventory variables |

## Running the playbooks

```bash
ansible-playbook -i <inventory> ssh_security_example.yml
```

Each playbook targets `hosts: all` and uses `become: true`. Adjust the host pattern or run with `--limit` to scope where they apply.
