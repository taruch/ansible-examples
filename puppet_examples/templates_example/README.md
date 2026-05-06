# Templates: ERB → Jinja2

Same MOTD rendered two ways. The single biggest paradigm shift for a Puppet user moving to Ansible is template syntax.

## Files

| Puppet | Ansible | Purpose |
|---|---|---|
| [motd.pp](motd.pp) | [motd.yml](motd.yml) | The "code" that renders the template |
| [motd.erb](motd.erb) | [motd.j2](motd.j2) | The template itself |

## Syntax mapping

| ERB (Puppet) | Jinja2 (Ansible) | Notes |
|---|---|---|
| `<%= @var %>` | `{{ var }}` | Expression — emits the value |
| `<% if @flag %>...<% end %>` | `{% if flag %}...{% endif %}` | Statement — control flow |
| `<% @items.each do \|i\| %>...<% end %>` | `{% for i in items %}...{% endfor %}` | Loop |
| Trailing `-%>` strips the newline | `{%- ... -%}` (and `trim_blocks`/`lstrip_blocks`) | Whitespace control |
| `<%# comment %>` | `{# comment #}` | Comment |
| `@variable` (instance var) | `variable` (no sigil) | ERB pulls from Puppet scope as `@name`; Jinja2 reads variables directly from the play/host scope |

## Variable plumbing

**Puppet:** any variable in scope at the call site (locals, class params, facts) is available to the template as `@name`. `template('mymodule/motd.erb')` looks for `mymodule/templates/motd.erb` on the Puppet master.

**Ansible:** the `template` module resolves `src:` against the playbook's `templates/` directory (or `<role>/templates/` when used in a role). Variables come from the play vars, role defaults, host_vars/group_vars, and gathered facts — all merged into the template's scope.

## Facts in templates

| Puppet | Ansible |
|---|---|
| `<%= @fqdn %>` (top-scope fact) | `{{ ansible_facts['fqdn'] }}` |
| `<%= scope['facts']['os']['family'] %>` | `{{ ansible_facts['os_family'] }}` |
| `<%= @os_release %>` (set as local) | `{{ ansible_facts['distribution_major_version'] }}` |

## Running

```bash
ansible-playbook -i <inventory> motd.yml
```

The Puppet manifest assumes module context (the `template()` function looks for `<module>/templates/motd.erb`). The .pp/.erb pair here illustrates the syntax — you'd normally drop them into `modules/profile/manifests/motd.pp` and `modules/profile/templates/motd.erb`.
