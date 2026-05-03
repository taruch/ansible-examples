# Language Features

An extensive collection of Ansible playbook examples demonstrating core language features, idioms, and integrations. Useful as a reference library for common patterns.

## Playbooks

### Core Features
- **`intro_example.yml`** — Basic playbook structure: async tasks, Jinja2 file templating, package installation, service management, and handlers triggered by file changes.
- **`intermediate_example.yml`** — Intermediate patterns combining multiple features.
- **`conditionals_part1.yml`** — Conditional variable file loading based on facts (e.g., OS-specific vars).
- **`conditionals_part2.yml`** — Additional conditional execution patterns (`when`, `failed_when`, `changed_when`).
- **`register_logic.yml`** — Using `register` to capture task output and branch logic on results.
- **`tags.yml`** — Selective task execution using `tags` and `--tags`/`--skip-tags`.
- **`prompts.yml`** — Interactive `vars_prompt` for gathering input at runtime.

### Loops
- **`loop_with_items.yml`** — Basic `loop` / `with_items` iteration.
- **`loop_nested.yml`** — Nested loops with `with_nested`.
- **`loop_plugins.yml`** — Various loop plugins (`with_dict`, `with_fileglob`, etc.).

### Variables & Filters
- **`custom_filters.yml`** — Writing and using custom Jinja2 filter plugins.
- **`upgraded_vars.yml`** — Variable scoping and precedence examples.
- **`selective_file_sources.yml`** — Selectively loading variable files based on conditions.
- **`complex_args.yml`** — Passing complex data structures as module arguments.

### Execution Control
- **`delegation.yml`** — Task delegation (`delegate_to`) for running tasks on a different host (e.g., removing from a load balancer before patching). Uses `serial` for batch control.
- **`batch_size_control.yml`** — Rolling updates with `serial` (fixed count or percentage).
- **`group_by.yml`** — Dynamic group creation with `group_by` based on gathered facts.
- **`ansible_pull.yml`** — Using `ansible-pull` for pull-mode configuration management.
- **`nested_playbooks.yml`** — Importing and including playbooks (`import_playbook`).

### Environment & System
- **`environment.yml`** — Setting environment variables for tasks and plays.
- **`file_secontext.yml`** — Managing SELinux file contexts with `sefcontext`.
- **`get_url.yml`** — Downloading files with the `get_url` module.
- **`group_commands.yml`** — Running commands as a specific group.
- **`user_commands.yml`** — User and group management.

### Services & Applications
- **`mysql.yml`** — MySQL installation and database/user management.
- **`postgresql.yml`** — PostgreSQL setup and configuration.
- **`rabbitmq.yml`** — RabbitMQ broker setup.
- **`zfs.yml`** — ZFS pool and dataset management.
- **`netscaler.yml`** — Citrix NetScaler load balancer integration.

### Cloud
- **`eucalyptus-ec2.yml`** — EC2/Eucalyptus instance management.
- **`cloudformation.yaml`** — AWS CloudFormation stack management.

### Roles
- **`roletest.yml`** / **`roletest2.yml`** — Role inclusion and variable passing examples.
