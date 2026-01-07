**Read this README to save yourself some headaches**


# Playbooks in this repo
 - filetree_export_24.yml for exporting on the command line from an AAP 2.4 instance to a local directory
 - filetree_export_25to_git.yml for exporting in AAP from an AAP 2.5 instance to a git repository
 - filetree_export_25.yml for exporting on the command line from an AAP 2.5/2.6 (w/gateway) instance to a local directory
 - filetree_import_25.yml to import on the command line to an AAP 2.5/2.6 (w/gateway) instance

# Exporting
To do an export from an Ansible Automation Platform system using the export playbooks, export the variables defined in the playbook vars (at the top):
```bash
export CONTROLLER_VERIFY_SSL=<true or false>
export CONTROLLER_HOST=<FQDN of 2.4 (or 2.5/2.6 respectively) controller>
export CONTROLLER_PASSWORD=<password>
export CONTROLLER_USERNAME=<username>
```

**None of these playbooks will export the actual secrets in the credential export.**\
**The 2.5 export is configured to change the "secret/encrypted" to a variable that can be imported from a vault.**

You can do a search for vaulted in the export directory to find all of these variables.
```
grep -R vaulted <export directory>
```
Example: password: "{{ vaulted_controller_credentials_controller_credential_password | default('$encrypted$') }}"

You might also want to keep in mind if you are exporting to import into a different system from the one you are exporting from, you might want to search for your current AAP control node.  Resources like control node credentials and current_instance_groups will have the current system and will need to be updated.


### Run the playbook:
```
ansible-navigator run -mstdout filetree_export_24.yml -vvv --eei=quay.io/truch/export24:1.0 --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD --penv=CONTROLLER_HOST --penv=CONTROLLER_VERIFY_SSL
```
or
```
ansible-navigator run -mstdout filetree_export_25.yml -vvv --eei=quay.io/truch/ee25:1.1 --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD --penv=CONTROLLER_HOST --penv=CONTROLLER_VERIFY_SSL
```
***These exports will not export the actual secrets.  The 2.5 export is configured to change the "secret/encrypted" to a variable that can be imported from a vault.***


# Importing to a 2.5/2.6 system
THIS CAN BE A PROTRACTED PROCESS. If you have any technical debt (and most of us do) in your current instance of AAP you are exporting from, you will have issues you need to work through to import into the new instance. See Issues / Considerations below.

To import to an Automation Platform 2.5 system, export the variables defined in the playbook vars for the AAP 2.5 system.
```bash
export CONTROLLER_VERIFY_SSL=<true or false>
export CONTROLLER_HOST=<FQDN of 2.4 (or 2.5/2.6 respectively) controller>
export CONTROLLER_PASSWORD=<password>
export CONTROLLER_USERNAME=<username>
```

### Run the playbook:
```
ansible-navigator run -mstdout filetree_import_25.yml -vvv --eei=quay.io/truch/ee25:1.1 --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD --penv=CONTROLLER_HOST --penv=CONTROLLER_VERIFY_SSL
```

**You can set 'file_path' to have a specific file read in and processed for troubleshooting.  Typically you would do this by adding it as an extra var when running the playbook.**
```
ansible-navigator run -mstdout filetree_import_25.yml -vvv --eei=quay.io/truch/ee25:1.1 --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD --penv=CONTROLLER_HOST --penv=CONTROLLER_VERIFY_SSL -e file_path='./Default/projects/13_Template_Demo.yaml'
```

# Considerations / Issues / Troubleshooting:

**Be aware that if you run the import multiple times, you will overwrite rather than "merge". Think about any credential that you require (such as an Ansible Hub) for syncing collections or source control for importing projects, which if they are overwritten with a blank credential can be a problem.  It might be a good idea to delete those, or to fix them.**

## Searching Logs
Look for the following in the playbook artifact (log file)):
failed: [localhost]
fatal: [localhost]: FAILED!

## ORGANIZATIONLESS
If you had resources in the 2.4 system that were not assigned to an organization, you will run into issues importing those resources into the AAP 2.5 system.  You have a couple choices.
- Fix them in your 2.4 instance before you do the export **(best)**
- Change the ORGANIZATIONLESS resources to a viable organization (works): find ./<export directory> -type f -exec sed -i 's/ORGANIZATIONLESS/Default/g' {} +
- Delete the ORGANIZATIONLESS resources in your export directory

---\

## AAP 2.4 to 2.6 Migration Guide: Authentication & Configuration

This guide outlines how to refactor your **Ansible Automation Platform (AAP) 2.4** Configuration as Code (CaC) for **AAP 2.6**.

In AAP 2.6, the architecture has changed: **Authentication is now handled by the Gateway service**, while system-level job settings remain in the **Controller**.

---

### 1. Architecture Overview

In AAP 2.4, the Controller (Django-based) handled LDAP directly. In AAP 2.6, a new Python-based **Gateway service** acts as the central authentication broker for the entire platform.

The Gateway uses a pluggable system. When you configure LDAP in 2.6, you are interacting with the `ansible-base` authentication framework rather than the old `django-auth-ldap` settings.

---

### 2. Refactored Configuration (`vars.yml`)

**Organizations and Teams do not transfer gracefully**
#### Teams:
Not all configuration exported from 2.4 will match up for 2.5/2.6:
find ./<export directory>/ -type f -exec sed -i 's/controller_teams/aap_teams/g' {} +

You will sometimes get an error about gateway_settings:
 TASK [infra.aap_configuration.gateway_settings : Update automation platform gateway Settings] ***
You can resolve this by adding a variable with an empty dictionary:
ansible-navigator run -mstdout filetree_import_25.yml -vvv --eei=quay.io/truch/ee25:1.3 --penv=CONTROLLER_USERNAME --penv=CONTROLLER_PASSWORD --penv=CONTROLLER_HOST --penv=CONTROLLER_VERIFY_SSL -e "gateway_settings={}"


#### Organizations:
Add your organizations to a gateway_organizations.yaml file at the root of your export.
```yaml
---
aap_organizations:
  - name: OrgA
    description: !unsafe
  - name: OrgB
    description: !unsafe
  - name: Central Inventory Org
    description: !unsafe
```

#### A. Gateway Authenticators (LDAP Connection)

This replaces the old `AUTH_LDAP_SERVER_URI`, `BIND_DN`, and `USER_SEARCH` settings.

```yaml
gateway_authenticators:
  - name: "Corporate LDAP"
    # This plugin handles the actual LDAP/AD handshake
    type: "ansible_base.authentication.authenticator_plugins.ldap"
    enabled: true
    configuration:
      SERVER_URI: "ldap://ec2-3-19-243-195.us-east-2.compute.amazonaws.com:389"
      BIND_DN: "CN=ec2-user,CN=Users,DC=ansible,DC=local"
      BIND_PASSWORD: "{{ vault_ldap_bind_password }}" # Plaintext required at API level
      START_TLS: false
      USER_SEARCH:
        - "CN=Users,DC=ansible,DC=local"
        - "SCOPE_SUBTREE"
        - "(cn=%(user)s)" # Python syntax is retained
      USER_ATTR_MAP:
        email: "mail"
        first_name: "givenName"
        last_name: "sn"
      GROUP_SEARCH:
        - "DC=ansible,DC=local"
        - "SCOPE_SUBTREE"
        - "(objectClass=group)"
      GROUP_TYPE: "ActiveDirectoryGroupType"
      GROUP_TYPE_PARAMS:
        name_attr: "cn"

```

#### B. Gateway Authenticator Maps (Group Permissions)

This replaces `AUTH_LDAP_ORGANIZATION_MAP` and `AUTH_LDAP_TEAM_MAP`. These maps define which LDAP groups grant specific access levels within the platform.

```yaml
gateway_authenticator_maps:
  # Map LDAP Group to Organization Admin
  - name: "LDAP Org Admin Map"
    authenticator: "Corporate LDAP"
    map_type: "organization"
    organization: "LDAP_Organization"
    role: "Organization Admin"
    triggers:
      groups:
        - "cn=ansible_admins,cn=groups,dc=ansible,dc=local"

  # Map LDAP Group to a specific Team
  - name: "Team A Mapping"
    authenticator: "Corporate LDAP"
    map_type: "team"
    organization: "LDAP_Organization"
    team: "TeamA"
    triggers:
      groups:
        - "cn=GroupA,cn=groups,dc=ansible,dc=local"

```

#### C. Controller Settings (System Behavior)

These settings remain in the Controller. LDAP-specific keys (`AUTH_LDAP_*`) have been removed from this section.

```yaml
controller_settings:
  - name: AWX_ISOLATION_BASE_PATH
    value: "/tmp"
  - name: MAX_FORKS
    value: 200
  - name: SESSION_COOKIE_AGE
    value: 180000
  - name: PENDO_TRACKING_STATE
    value: "detailed"

```

---

### 3. Execution Control

To ensure the dispatcher runs only the necessary roles and avoids errors on empty default settings (like `gateway_settings`), define the explicit dispatch list in your `vars.yml`.

```yaml
gateway_dispatch_roles:
  - gateway_organizations
  - gateway_teams
  - gateway_authenticators
  - gateway_authenticator_maps
  # gateway_settings is omitted to prevent 'missing settings' errors

```


#### Important Notes

* **Passwords:** The Gateway requires the `BIND_PASSWORD` in plaintext during the API call. Protect this value using **Ansible Vault**.
* **Pre-requisites:** The `LDAP_Organization` and `TeamA` objects must exist. It is recommended to include `gateway_organizations` and `gateway_teams` in your dispatch list to create them dynamically before the maps are applied.



