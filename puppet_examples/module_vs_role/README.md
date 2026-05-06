# Puppet module → Ansible role

A Puppet **module** and an Ansible **role** are the same idea: a reusable, parameterized unit of configuration with a conventional directory layout. The webserver implementation in this directory is identical in behavior; only the layout and syntax differ.

## Side-by-side layout

```
puppet/                                ansible/
├── modules/                           ├── roles/
│   └── webserver/                     │   └── webserver/
│       ├── manifests/                 │       ├── defaults/
│       │   └── init.pp                │       │   └── main.yml
│       └── templates/                 │       ├── handlers/
│           └── index.html.erb         │       │   └── main.yml
└── site.pp                            │       ├── tasks/
                                       │       │   └── main.yml
                                       │       └── templates/
                                       │           └── index.html.j2
                                       └── playbook.yml
```

## Directory mapping

| Puppet module | Ansible role | What goes here |
|---|---|---|
| `manifests/init.pp` | `tasks/main.yml` | The work — resources/tasks |
| Class parameters with defaults | `defaults/main.yml` | Default variable values, lowest precedence |
| `data/*.yaml` (Hiera-in-module) | `vars/main.yml` | Module-internal vars, higher precedence |
| `templates/*.erb` | `templates/*.j2` | Rendered templates |
| `files/` | `files/` | Static files copied to nodes |
| `notify => Service[...]` | `handlers/main.yml` (triggered via `notify:`) | Restart-on-change actions |
| `metadata.json` | `meta/main.yml` | Module metadata, dependencies |
| `examples/` / `spec/` | `molecule/` / `tests/` | Tests and example usage |

## Invocation

**Puppet** — declare the class with parameters:
```puppet
# site.pp
node default {
  class { 'webserver':
    site_title => 'Hello from Puppet',
  }
}
```

**Ansible** — apply the role with vars:
```yaml
# playbook.yml
- hosts: all
  become: true
  roles:
    - role: webserver
      vars:
        site_title: Hello from Ansible
```

## Variable precedence

Both systems layer variables, but the rules differ.

**Puppet** (lowest → highest):
1. Class parameter defaults (in `init.pp`)
2. Hiera data (environment, then node-specific)
3. Explicit override at the call site (`class { ... }`)

**Ansible** (lowest → highest, abbreviated):
1. `defaults/main.yml`
2. `inventory` vars / `group_vars` / `host_vars`
3. `vars/main.yml` (role)
4. Play `vars:`
5. Task `vars:`
6. `--extra-vars` on the CLI

The practical rule: **Puppet defaults live in the class signature; Ansible defaults live in `defaults/main.yml`** — and both are designed to be overridden from outside the module/role.

## Running

```bash
# Puppet (with the module on the modulepath)
puppet apply --modulepath=puppet/modules puppet/site.pp

# Ansible
ansible-playbook -i <inventory> ansible/playbook.yml
```
