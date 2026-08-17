# Dynamic Inventory Examples

This directory contains comprehensive examples of dynamic inventory configurations for various infrastructure sources. Each example demonstrates rich group composition patterns and best practices for organizing hosts dynamically.

## What is Dynamic Inventory?

Dynamic inventory allows Ansible to query external systems (cloud providers, virtualization platforms, CMDBs, etc.) to automatically discover and group hosts at runtime. This eliminates the need to maintain static inventory files and ensures your inventory is always up-to-date.

## Available Inventory Sources

| Source | Plugin | File | Groups | Description |
|--------|--------|------|--------|-------------|
| **AWS EC2** | `amazon.aws.aws_ec2` | [aws_enhanced.yml](aws/aws_enhanced.yml) | 80+ | Enhanced AWS inventory with comprehensive tagging patterns |
| **Azure** | `azure.azcollection.azure_rm` | [azure.yml](azure/azure.yml) | 60+ | Azure VMs with resource group, location, and tag-based groups |
| **VMware vSphere** | `community.vmware.vmware_vm_inventory` | [vmware.yml](vmware/vmware.yml) | 50+ | vCenter VMs grouped by cluster, folder, OS, and properties |
| **OpenShift Virtualization** | `kubernetes.core.k8s` | [openshift_virt.yml](openshift_virt/openshift_virt.yml) | 40+ | KubeVirt VMs with namespace and label-based grouping |
| **Microsoft AD** | `community.windows.ldap` | [microsoft_ad.yml](microsoft_ad/microsoft_ad.yml) | 50+ | AD computer objects via LDAP with OU and group-based organization |
| **Infoblox NIOS** | `infoblox.nios_modules.nios_inventory` | [infoblox.yml](infoblox/infoblox.yml) | 60+ | IPAM/DNS records with network, location, and extensible attribute grouping |
| **NetBox** | `netbox.netbox.nb_inventory` | [netbox.yml](netbox/netbox.yml) | 70+ | IPAM/DCIM with site, rack, role, and custom field grouping |
| **Nutanix AHV** | `nutanix.ncp.ntnx_vms_inventory` | [nutanix.yml](nutanix/nutanix.yml) | 60+ | Nutanix VMs with cluster, category, and resource-based groups |
| **Red Hat Satellite** | `theforeman.foreman.foreman` | [example_source_variables.yml](satellite/example_source_variables.yml) | 10+ | Satellite/Foreman managed hosts |
| **ServiceNow** | `servicenow.itsm.now` | [servicenow.yml](ServiceNow/servicenow.yml) | 5+ | CMDB computer inventory |

## Inventory Configuration Sections

Dynamic inventory files use several configuration sections. Here's what each one does:

### **`plugin`**
**Purpose:** Specifies which inventory plugin to use  
**Required:** Yes  
**Example:** `plugin: amazon.aws.aws_ec2`  
**Description:** Tells Ansible which collection and plugin will provide the inventory. Must match an installed inventory plugin.

### **`compose`**
**Purpose:** Create or modify host variables using Jinja2 expressions  
**Required:** No  
**When to use:** Transform source data into useful variables, set connection parameters, calculate derived values  
**Example:**
```yaml
compose:
  # Set ansible_host from cloud provider data
  ansible_host: public_ip_address | default(private_ip_address)
  
  # Create custom variable from multiple fields
  vm_size: |
    'large' if vcpus >= 4 else 'small'
```
**Tips:**
- Set `ansible_host`, `ansible_user`, `ansible_connection` here
- Use Jinja2 filters to transform data
- Can reference any property from the source system

### **`groups`**
**Purpose:** Create static groups using simple boolean expressions  
**Required:** No  
**When to use:** Create groups based on simple true/false conditions  
**Example:**
```yaml
groups:
  # All instances from this source
  cloud_aws: true
  
  # Running instances only
  aws_running: state.name == 'running'
  
  # Instances with public IPs
  has_public_ip: public_ip_address is defined
```
**Tips:**
- Use `true` to add all hosts to a group
- Use simple comparisons for basic filtering
- Good for infrastructure-wide groups

### **`keyed_groups`**
**Purpose:** Dynamically create groups from host properties/tags  
**Required:** No  
**When to use:** Generate many groups automatically from tags, labels, or attributes  
**Example:**
```yaml
keyed_groups:
  # Group by region → creates groups like "aws_us_east_1"
  - key: placement.region
    prefix: aws
  
  # Group by tags → creates "env_production", "env_dev"
  - key: tags.Environment | default('untagged')
    prefix: env
  
  # Group by list of tags (creates multiple groups)
  - key: tags | dict2items | map(attribute='key')
    prefix: tag
```
**Tips:**
- Creates one group per unique value
- Use `prefix` to namespace the groups
- Use `separator` to change delimiter (default: `_`)
- Can use Jinja2 filters on the key

### **`conditional_groups`**
**Purpose:** Create groups using complex logic and multiple conditions  
**Required:** No  
**When to use:** When simple groups aren't enough; need AND/OR logic, string matching, calculations  
**Example:**
```yaml
conditional_groups:
  # Production (multiple criteria with OR)
  production: |
    tags.Environment == 'production' or
    'prod' in name.lower() or
    placement.region == 'us-east-1'
  
  # Web servers (pattern matching)
  webservers: |
    'web' in tags.Role | default('') or
    'nginx' in name.lower()
  
  # Mission critical (complex logic)
  mission_critical: |
    tags.Tier == '1' and
    vcpus >= 4 and
    memory_gb >= 16
```
**Tips:**
- Can use multi-line expressions with `|`
- Supports all Jinja2 filters and tests
- Great for workload types, compliance, patch groups

### **`hostnames`**
**Purpose:** Define which field(s) to use as the inventory hostname  
**Required:** No (defaults to plugin-specific field)  
**When to use:** Control how hosts appear in inventory  
**Example:**
```yaml
hostnames:
  - tag:Name              # Try this first
  - dns-name              # Then this
  - private-dns-name      # Finally this
```
**Tips:**
- Ansible tries each in order until one has a value
- First match wins
- Must be unique across inventory

### **`filters`** / **`query_filters`**
**Purpose:** Limit which resources are queried from the source (API-side filtering)  
**Required:** No  
**When to use:** Reduce API calls and inventory size  
**Example:**
```yaml
# AWS example
filters:
  instance-state-name: running
  tag:Environment: production

# NetBox example
query_filters:
  - role: server
  - status: active
```
**Tips:**
- Reduces API overhead
- Filters happen on source system (fast)
- Different syntax per plugin

### **`include_filters`** / **`exclude_filters`**
**Purpose:** Include or exclude resources using OR logic (after API query)  
**Required:** No  
**When to use:** More flexible filtering than basic filters  
**Example:**
```yaml
# Include production OR staging
include_filters:
  - tag:Environment: production
  - tag:Environment: staging

# Exclude anything marked DoNotManage
exclude_filters:
  - tag:DoNotManage: "true"
```

### **`cache`** / **`cache_plugin`** / **`cache_timeout`**
**Purpose:** Cache inventory data to improve performance  
**Required:** No (but recommended for large inventories)  
**When to use:** API queries are slow, inventory is large (>100 hosts), or you run inventory frequently  
**Example:**
```yaml
cache: yes
cache_plugin: jsonfile
cache_timeout: 300  # 5 minutes in seconds
cache_connection: /tmp/aws_inventory_cache
cache_prefix: aws_ec2
```
**Tips:**
- Dramatically speeds up repeat queries
- Set timeout based on how often infrastructure changes
- Use different prefixes for different inventory sources

### **`validate_certs`**
**Purpose:** Enable/disable SSL certificate validation  
**Required:** No (defaults to true)  
**When to use:** Self-signed certs, lab environments  
**Example:**
```yaml
validate_certs: false  # Use with caution
```
**Tips:**
- Set to `false` only for dev/lab environments
- Security risk in production
- Better solution: add CA cert to trust store

### **`regions`** / **`locations`** / **`datacenters`**
**Purpose:** Limit queries to specific geographic regions (cloud-specific)  
**Required:** No  
**Example:**
```yaml
# AWS
regions:
  - us-east-1
  - us-west-2

# Azure
locations:
  - eastus
  - westus2
```

## Quick Start

### 1. Install Required Collections

Each inventory source requires specific Ansible collections:

```bash
# AWS
ansible-galaxy collection install amazon.aws

# Azure
ansible-galaxy collection install azure.azcollection

# VMware
ansible-galaxy collection install community.vmware

# OpenShift/Kubernetes
ansible-galaxy collection install kubernetes.core

# Microsoft AD
ansible-galaxy collection install community.windows

# Infoblox
ansible-galaxy collection install infoblox.nios_modules

# NetBox
ansible-galaxy collection install netbox.netbox

# Nutanix
ansible-galaxy collection install nutanix.ncp

# Satellite/Foreman
ansible-galaxy collection install theforeman.foreman

# ServiceNow
ansible-galaxy collection install servicenow.itsm
```

### 2. Configure Authentication

Each source has different authentication requirements. See the Authentication section below.

### 3. Test the Inventory

```bash
# Test AWS inventory
ansible-inventory -i inventory_examples/aws/aws_enhanced.yml --list

# Graph the inventory structure
ansible-inventory -i inventory_examples/aws/aws_enhanced.yml --graph

# Show specific host details
ansible-inventory -i inventory_examples/aws/aws_enhanced.yml --host hostname

# Use with playbooks
ansible-playbook -i inventory_examples/azure/azure.yml my_playbook.yml
```

## Authentication

### AWS
```bash
# Option 1: Environment variables (recommended)
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export AWS_DEFAULT_REGION="us-east-1"

# Option 2: AWS CLI credentials
aws configure

# Option 3: IAM role (when running on EC2)
# No configuration needed - uses instance metadata
```

### Azure
```bash
# Option 1: Service Principal (recommended for automation)
export AZURE_SUBSCRIPTION_ID="your_subscription_id"
export AZURE_CLIENT_ID="your_client_id"
export AZURE_SECRET="your_secret"
export AZURE_TENANT="your_tenant_id"

# Option 2: Azure CLI (for local development)
az login

# Option 3: Managed Identity (when running on Azure VM)
# No configuration needed
```

### VMware vSphere
```bash
# Environment variables
export VMWARE_HOST="vcenter.example.com"
export VMWARE_USER="administrator@vsphere.local"
export VMWARE_PASSWORD="your_password"

# Or configure directly in the inventory file (use vault for password)
```

### OpenShift Virtualization
```bash
# Option 1: kubeconfig file (default)
export K8S_AUTH_KUBECONFIG=~/.kube/config
export K8S_AUTH_CONTEXT=openshift-prod

# Option 2: Service account token
export K8S_AUTH_API_KEY="your_service_account_token"
export K8S_AUTH_HOST="https://api.openshift.example.com:6443"

# Option 3: oc login (uses current context)
oc login https://api.openshift.example.com:6443
```

### Microsoft Active Directory
```bash
# Environment variables
export ANSIBLE_LDAP_SERVER="dc01.example.com"
export ANSIBLE_LDAP_USERNAME="CN=ServiceAccount,OU=ServiceAccounts,DC=example,DC=com"
export ANSIBLE_LDAP_PASSWORD="your_password"

# Or configure in inventory file with vault
```

### Infoblox NIOS
```bash
# Environment variables
export INFOBLOX_HOST="nios.example.com"
export INFOBLOX_USERNAME="admin"
export INFOBLOX_PASSWORD="your_password"

# Or configure in inventory file
# provider:
#   host: nios.example.com
#   username: admin
#   password: "{{ lookup('env', 'INFOBLOX_PASSWORD') }}"
#   wapi_version: "2.12"
```

### NetBox
```bash
# Environment variables
export NETBOX_API="https://netbox.example.com"
export NETBOX_TOKEN="your_api_token"

# Or configure in inventory file
# api_endpoint: https://netbox.example.com
# token: "{{ lookup('env', 'NETBOX_TOKEN') }}"
```

### Nutanix AHV
```bash
# Environment variables
export NUTANIX_HOST="prism-central.example.com"
export NUTANIX_USERNAME="admin"
export NUTANIX_PASSWORD="your_password"
export NUTANIX_PORT="9440"

# Or configure in inventory file
# nutanix_hostname: prism-central.example.com
# nutanix_username: admin
# nutanix_password: "{{ lookup('env', 'NUTANIX_PASSWORD') }}"
# nutanix_port: 9440
```

### Red Hat Satellite
```bash
# Environment variables
export FOREMAN_SERVER="https://satellite.example.com"
export FOREMAN_USER="admin"
export FOREMAN_PASSWORD="your_password"
```

### ServiceNow
```bash
# Environment variables
export SN_HOST="instance.service-now.com"
export SN_USERNAME="admin"
export SN_PASSWORD="your_password"
```

## Group Patterns

Each inventory source creates dynamic groups using these patterns:

### Infrastructure Groups
- **Region/Location**: `aws_us_east_1`, `location_eastus`, `dc_datacenter1`
- **Availability Zones**: `az_us_east_1a`, `azure_zonal`
- **Networks**: `vpc_vpc123`, `vnet_production`, `net_vlan100`
- **Clusters**: `cluster_prod_cluster`, `pool_production`

### Resource Sizing Groups
- **Instance Types**: `type_t3_medium`, `vmsize_Standard_D4s_v3`, `family_t3`
- **CPU**: `vcpu_4`, `high_cpu`, `cpu_8`
- **Memory**: `memory_gb_16`, `high_memory`
- **Size Tiers**: `size_small`, `size_large`, `premium_tier`

### Operating System Groups
- **Platform**: `platform_linux`, `platform_windows`, `os_linux`
- **Distribution**: `os_rhel`, `os_ubuntu`, `os_amazon_linux`, `rhel`, `ubuntu`
- **Version**: `osver_rhel_8`, `windows_2022`, `windows_2019`
- **Guest Family**: `guest_linuxGuest`, `guest_windowsGuest`

### Workload Type Groups
- **Web Servers**: `webservers`
- **Databases**: `databases`
- **Application Servers**: `appservers`
- **Load Balancers**: `loadbalancers`
- **Kubernetes**: `kubernetes`, `eks_nodes`
- **Domain Controllers**: `domain_controllers`

### Lifecycle Groups
- **Environment**: `production`, `development`, `staging`, `env_production`
- **Age**: `aws_new`, `aws_old`, `recently_created`, `stale_computers`
- **State**: `aws_running`, `aws_stopped`, `vmware_running`, `virt_running`

### Operations Groups
- **Patch Groups**: `patch_group_a`, `patch_sunday`, `patch_monday`
- **Backup**: `backup_daily`, `backup_weekly`, `backup_required`
- **Monitoring**: `aws_detailed_monitoring`, `vmtools_ok`

### Compliance & Security Groups
- **Compliance**: `compliance_pci`, `compliance_hipaa`, `compliance_sox`
- **Data Classification**: `data_internal`, `data_confidential`
- **Criticality**: `mission_critical`, `high_availability`

### Organizational Groups
- **Tags/Labels**: `app_nginx`, `owner_teamA`, `project_website`, `team_devops`
- **Cost Center**: `costcenter_finance`, `cost_center_unassigned`
- **OU/Folder**: `ou_servers`, `folder_production`

## Advanced Usage

### Using Multiple Inventory Sources

Create a directory and place multiple inventory files in it:

```bash
mkdir -p inventories/production
cp inventory_examples/aws/aws_enhanced.yml inventories/production/aws.yml
cp inventory_examples/azure/azure.yml inventories/production/azure.yml
cp inventory_examples/vmware/vmware.yml inventories/production/vmware.yml

# Use the directory as inventory
ansible-playbook -i inventories/production my_playbook.yml
```

Ansible will merge all inventory sources, creating a unified inventory with hosts from all platforms.

### Inventory Caching

Enable caching to improve performance for large inventories:

```yaml
# Add to your inventory file
cache: yes
cache_plugin: jsonfile
cache_timeout: 3600  # 1 hour
cache_connection: /tmp/ansible_inventory_cache
cache_prefix: my_inventory
```

### Filtering in Playbooks

Use dynamic groups in your playbooks:

```yaml
---
- name: Patch all production web servers
  hosts: production:&webservers
  tasks:
    - name: Update packages
      package:
        name: '*'
        state: latest

- name: Configure monitoring on high memory VMs
  hosts: high_memory:&aws_running
  tasks:
    - name: Install monitoring agent
      include_role:
        name: monitoring

- name: Backup all databases in us-east-1
  hosts: databases:&aws_us_east_1
  tasks:
    - name: Run backup
      include_role:
        name: database_backup
```

### Creating Custom Groups

Add custom conditional groups to any inventory file:

```yaml
conditional_groups:
  # Expensive instances (large + production)
  expensive: |
    'production' in group_names and
    ('large' in instance_type or 'xlarge' in instance_type)

  # Needs attention (old + untagged)
  needs_attention: |
    instance_age_days > 365 and
    (tags.Owner is not defined or tags.Owner == '')

  # Patch tonight (specific criteria)
  patch_tonight: |
    tags.PatchGroup == 'A' and
    ansible_date_time.weekday == '6' and  # Sunday
    'production' not in group_names
```

## Best Practices

### 1. Use Descriptive Group Names
- ✅ Good: `production_webservers`, `patch_group_sunday`, `compliance_pci`
- ❌ Bad: `group1`, `servers`, `misc`

### 2. Layer Your Groups
```yaml
# Combine groups for precision
hosts: production:&databases:&aws_us_east_1
```

### 3. Leverage Tags/Labels
Always tag your resources:
```
Environment: production
Application: web
Owner: team-platform
PatchGroup: A
Backup: daily
```

### 4. Use Caching for Large Inventories
- Enable caching for inventories with >100 hosts
- Set appropriate timeout (5-60 minutes)

### 5. Secure Your Credentials
```bash
# Never hardcode credentials
# Use environment variables or Ansible Vault

# Example with vault
ansible-vault encrypt_string 'mypassword' --name 'vmware_password'
```

### 6. Test Before Production
```bash
# Always test inventory changes
ansible-inventory -i my_inventory.yml --list | jq .

# Verify specific groups exist
ansible-inventory -i my_inventory.yml --graph | grep production
```

### 7. Document Custom Groups
Add comments to your inventory files explaining complex conditional groups.

## Troubleshooting

### Inventory Returns No Hosts

```bash
# Check authentication
ansible-inventory -i inventory.yml --list -vvv

# Verify filters
# Remove restrictive filters temporarily to see all hosts

# Check API permissions
# Ensure service account has read permissions
```

### Slow Inventory Performance

```bash
# Enable caching
cache: yes
cache_timeout: 300

# Reduce scope
# Use filters to query fewer resources
# Query fewer regions/subscriptions

# Use --limit
ansible-playbook -i inventory.yml playbook.yml --limit production
```

### Groups Not Created

```bash
# Check for undefined variables
ansible-inventory -i inventory.yml --list | jq '.["_meta"]["hostvars"]'

# Verify keyed_groups key exists
# The property must exist on the resource

# Check conditional group syntax
# Use single quotes for complex expressions
```

### Authentication Failures

```bash
# Test authentication separately
# AWS
aws sts get-caller-identity

# Azure
az account show

# VMware
govc ls  # or use PowerCLI

# OpenShift
oc whoami
```

## Examples by Use Case

### Patch Management

```yaml
# Inventory with patch groups
keyed_groups:
  - key: tags.PatchGroup
    prefix: patch

conditional_groups:
  patch_sunday: tags.PatchGroup == 'A'
  patch_tuesday: tags.PatchGroup == 'B'
```

### Multi-Cloud Management

```bash
# Use multiple inventory sources
ansible-playbook \
  -i aws/aws_enhanced.yml \
  -i azure/azure.yml \
  -i vmware/vmware.yml \
  site.yml
```

### Disaster Recovery

```yaml
conditional_groups:
  dr_primary: tags.DRSite == 'primary'
  dr_secondary: tags.DRSite == 'secondary'
  dr_critical: tags.DRTier == '1'
```

### Compliance Reporting

```yaml
conditional_groups:
  compliance_pci: tags.Compliance == 'PCI'
  compliance_hipaa: tags.Compliance == 'HIPAA'
  requires_encryption: tags.RequiresEncryption == 'yes'
```

## Contributing

When adding new inventory examples:

1. Include comprehensive comments
2. Add at least 20 dynamic groups
3. Demonstrate both keyed_groups and conditional_groups
4. Document authentication requirements
5. Test with real infrastructure

## Resources

- [Ansible Inventory Guide](https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html)
- [Dynamic Inventory Docs](https://docs.ansible.com/ansible/latest/user_guide/intro_dynamic_inventory.html)
- [Inventory Plugins](https://docs.ansible.com/ansible/latest/plugins/inventory.html)

## Support

For issues with specific inventory plugins:
- AWS: https://github.com/ansible-collections/amazon.aws
- Azure: https://github.com/ansible-collections/azure
- VMware: https://github.com/ansible-collections/community.vmware
- Kubernetes: https://github.com/ansible-collections/kubernetes.core
- Windows: https://github.com/ansible-collections/community.windows
