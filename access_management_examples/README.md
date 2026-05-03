# Access Management Examples

Playbooks for managing access control in Ansible Automation Platform (AAP) 2.5 and Windows Active Directory.

## Playbooks

### `create_ad_groups_users.yml`
Creates Active Directory groups and users on a Windows domain controller using the `microsoft.ad` collection. Sets up organizational groups (`orga_admins`, `orgb_admins`, `central_inventory_admins`) and corresponding user accounts for testing LDAP-backed AAP access control.

### `filetree_import_25.yml`
Imports an AAP 2.5 configuration filetree into a running Controller instance. Authenticates via OAuth token, uses `infra.aap_configuration.filetree_read` to parse exported configuration files, then applies them with the `dispatch` role.

## Requirements
- `infra.aap_configuration` collection
- `microsoft.ad` collection
- AAP 2.5 controller endpoint and admin credentials
