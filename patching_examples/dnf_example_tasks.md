# DNF Example Tasks

## Handling missing or unavailable packages

### Approach 1: Loop individually with `ignore_errors: true` (not my favorite)

Running each package as an individual item allows Ansible to record a failure for missing packages while proceeding to install all remaining valid ones.

```yaml
- name: Install Basic packages individually
  ansible.builtin.dnf:
    name: "{{ item }}"
    state: present
  loop:
    - katello-host-tools
    - katello-host-tools-tracer
    - insights-client
    - python3-psutil
    - telnet
    - krb5-libs
    - authconfig
    - nmap
    - net-tools
    - redhat-lsb-core
    # ... rest of package list ...
  ignore_errors: true
```

### Approach 2 (recommended): Pre-filter with `dnf list`, then bulk install

Pre-query each package with `dnf list {{ item }}`, then install only the ones that exist, in a single bulk transaction.

```yaml
- name: Check package existence (installed or available)
  ansible.builtin.command: "dnf list {{ item }}"
  loop:
    - katello-host-tools
    - nfs-utils
    # ... rest of package list ...
  register: pkg_check
  failed_when: false
  changed_when: false

- name: Build list of packages that actually exist
  ansible.builtin.set_fact:
    valid_packages: "{{ pkg_check.results | selectattr('rc', 'equalto', 0) | map(attribute='item') | list }}"

- name: Install available packages in bulk
  ansible.builtin.dnf:
    name: "{{ valid_packages }}"
    state: present
```

Runnable example: [`dnf_bulk_install_example.yml`](dnf_bulk_install_example.yml).

## Handling broken dependencies during `dnf update`

### 1. Add `skip_broken: true` (primary fix)

Tells DNF to remove packages with broken dependencies or missing mirror files from the update queue and proceed with updating everything else.

```yaml
- name: Update all packages, skipping broken dependencies
  ansible.builtin.dnf:
    name: "*"
    state: latest
    skip_broken: true
```

### 2. Add `nobest: true`

If an update fails because the absolute newest ("best") package version has an unmet dependency, `nobest: true` allows DNF to fall back to an updated version that does satisfy dependencies.

```yaml
- name: Update packages with version fallback
  ansible.builtin.dnf:
    name: "*"
    state: latest
    nobest: true
    skip_broken: true
```

### 3. Refresh cache with `update_cache: true`

If updates fail because local repo metadata points to package versions that no longer exist on the upstream mirror, forcing a metadata refresh before updating resolves the issue.

```yaml
- name: Force cache update and apply upgrades
  ansible.builtin.dnf:
    name: "*"
    state: latest
    update_cache: true
    skip_broken: true
```

### 4. Exclude specific failing packages

If a specific third-party package consistently breaks the update transaction, exclude it explicitly:

```yaml
- name: Update all except problematic package
  ansible.builtin.dnf:
    name: "*"
    state: latest
    exclude: "problematic-package-name*"
    skip_broken: true
```
