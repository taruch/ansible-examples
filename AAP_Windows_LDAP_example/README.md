# AAP Windows LDAP Example

Demonstrates integrating Ansible Automation Platform (AAP) 2.5 with Windows Active Directory via LDAP authentication. Includes playbooks to set up AD groups/users and import the corresponding AAP configuration.

## Playbooks

### `AAP_LDAP_Setup.yml`
Imports an AAP 2.5 configuration from an exported filetree structure into a running AAP instance. Uses the `infra.aap_configuration` collection's `filetree_read` and `dispatch` roles to configure organizations, teams, credentials, job templates, authenticators, gateway settings, and more. Handles OAuth token creation before import and revocation on cleanup.

### `create_ad_groups_users.yml`
Creates the Active Directory groups and users required for LDAP-backed AAP access control using the `microsoft.ad` collection. Creates organizational groups (`AAP_Team_A`, `AAP_Team_B`, `AAP_Master_Access`, etc.) with nested membership, plus corresponding admin and standard user accounts on a Windows domain controller.

## Export Data (`export_25_1/`)
Contains the exported AAP 2.5 configuration filetree (YAML files for organizations, authenticators, authenticator maps, HTTP ports, and vaulted variables) that `AAP_LDAP_Setup.yml` imports.

## Requirements
- `infra.aap_configuration` collection
- `microsoft.ad` collection
- AAP 2.5 controller and gateway endpoints configured as inventory variables
- Vault password for `vaulted_variables.yml`
