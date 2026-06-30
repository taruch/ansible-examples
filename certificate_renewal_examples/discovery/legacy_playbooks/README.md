# Legacy Standalone Playbooks

These playbooks have been superseded by the **role-based architecture** in the parent directory.

## Migration Guide

### Old Approach (Standalone Playbooks)

```bash
# Old: Multiple separate playbooks
ansible-playbook config_based_cert_discovery.yml
ansible-playbook windows_comprehensive_cert_discovery.yml
ansible-playbook generate_consolidated_report.yml
```

### New Approach (Unified Role-Based Playbook)

```bash
# New: One playbook for all platforms
cd ../playbooks
ansible-playbook -i ../inventory.yml discover_certificates.yml
```

## What Changed

1. **Modular Roles**: Discovery logic moved to reusable roles
   - `cert_discovery_config_based`
   - `cert_discovery_windows`
   - `cert_report_generator`

2. **Intelligent Routing**: Playbook auto-detects OS and installed packages

3. **Better Reusability**: Roles can be used in your own playbooks or as dependencies

4. **Cleaner Structure**: Separation of concerns (discovery vs reporting)

## Files in This Directory

- `config_based_cert_discovery.yml` - Configuration parsing approach
- `intelligent_cert_discovery.yml` - Filesystem search approach
- `windows_comprehensive_cert_discovery.yml` - Windows-specific discovery
- `generate_consolidated_report.yml` - Report aggregation

## Why These Were Replaced

- **Duplicated Logic**: Each playbook had similar setup/teardown code
- **Hard to Maintain**: Changes had to be replicated across multiple files
- **Limited Reusability**: Couldn't easily integrate into other workflows
- **No OS Detection**: Required manual playbook selection

## Recommendation

Use the new unified playbook: `../playbooks/discover_certificates.yml`

For documentation, see:
- [Main README](../README.md)
- [Role Documentation](../roles/README.md)
