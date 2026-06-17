# Preserving extra_vars Comments During AAP 2.4 to 2.6 Migration

## Problem

When migrating job templates from AAP 2.4 to AAP 2.6 using the filetree export/import process, **YAML comments in the `extra_vars` field are stripped** during the migration. This is a significant issue because many teams use these comments to document:

- What variables are required
- Expected formats and examples
- Who should be contacted for questions
- Links to documentation

The comments are lost because the filetree export process parses the YAML (which strips comments) and then re-serializes it.

## Solution Overview

This solution uses a two-step process to preserve and restore comments:

1. **Before export**: Extract the raw `extra_vars` field (with comments) directly from AAP 2.4 API
2. **After import**: Restore the preserved `extra_vars` to AAP 2.6 via API

```
AAP 2.4                          AAP 2.6
┌─────────────┐                 ┌─────────────┐
│ Job Template│                 │ Job Template│
│ extra_vars: │                 │ extra_vars: │
│   # Comment │  ─────┐         │   var: val  │ ◄───┐
│   var: val  │       │         │             │     │
└─────────────┘       │         └─────────────┘     │
                      │                              │
      │               │                              │
      │               ▼                              │
      │         ┌──────────────┐                     │
      │         │  Preserved   │                     │
      │         │  Comments    │                     │
      │         │  JSON file   │─────────────────────┘
      │         └──────────────┘
      │
      ▼
┌─────────────┐       ┌─────────────┐
│  Filetree   │──────▶│  Filetree   │
│   Export    │       │   Import    │
└─────────────┘       └─────────────┘
  (comments lost)     (comments missing)
```

## Prerequisites

- Access to AAP 2.4 API (source system)
- Access to AAP 2.6 API (target system)
- Ansible 2.9+ with `ansible.builtin.uri` module
- Network connectivity to both AAP instances

## Migration Workflow

### Step 1: Extract Comments from AAP 2.4

**IMPORTANT**: Run this BEFORE your filetree export!

```bash
# Set connection details for AAP 2.4
export AAP24_HOST=controller24.example.com
export AAP24_USERNAME=admin
export AAP24_PASSWORD=yourpassword

# Extract and preserve extra_vars with comments
ansible-playbook extract_extra_vars_comments.yml
```

This creates:
- `preserved_comments/extra_vars_with_comments.json` - The preserved data
- `preserved_comments/extraction_report.md` - Human-readable report

**Review the extraction_report.md** to verify comments were captured correctly.

### Step 2: Run Your Normal Filetree Export

Proceed with your standard AAP 2.4 export process:

```bash
ansible-playbook filetree_export_24.yml
```

### Step 3: Import to AAP 2.6

Run your standard filetree import to AAP 2.6:

```bash
ansible-playbook filetree_import_26.yml
```

At this point, the job templates exist in AAP 2.6 but the `extra_vars` comments are missing.

### Step 4: Restore Comments to AAP 2.6

```bash
# Set connection details for AAP 2.6
export AAP26_HOST=controller26.example.com
export AAP26_USERNAME=admin
export AAP26_PASSWORD=yourpassword

# First, run in dry-run mode to preview changes
export DRY_RUN=true
ansible-playbook restore_extra_vars_comments.yml

# Review the restoration_report.md, then apply the changes
export DRY_RUN=false
ansible-playbook restore_extra_vars_comments.yml
```

This creates:
- `preserved_comments/restoration_report.md` - Details of what was updated

### Step 5: Verify

1. Log into AAP 2.6 web UI
2. Navigate to a job template that had comments in `extra_vars`
3. Verify the comments are present

## Files Included

| File | Purpose |
|------|---------|
| `extract_extra_vars_comments.yml` | Extracts extra_vars from AAP 2.4 API |
| `restore_extra_vars_comments.yml` | Restores extra_vars to AAP 2.6 API |
| `README_EXTRA_VARS_MIGRATION.md` | This documentation |

## How It Works

### Extraction (extract_extra_vars_comments.yml)

1. Queries `/api/v2/job_templates/` from AAP 2.4
2. Handles pagination to get all templates
3. Extracts the `extra_vars` field for each template
4. Saves to JSON file with structure:
   ```json
   [
     {
       "id": 42,
       "name": "LINUX / Patching",
       "organization": "Default",
       "extra_vars": "# Specify target hosts\n# Example: webservers\ntarget: all\n"
     }
   ]
   ```

### Restoration (restore_extra_vars_comments.yml)

1. Loads the preserved JSON file
2. Queries AAP 2.6 to get current job template IDs
3. Matches templates by name
4. Uses PATCH API calls to update `extra_vars` field
5. Generates a report of what was changed

## Template Matching

Templates are matched between AAP 2.4 and 2.6 by **name**. If you renamed templates during migration, you'll need to manually edit the preserved JSON file to update the names.

## Edge Cases

### Template Not Found in AAP 2.6

If a template exists in the preserved data but not in AAP 2.6:
- It will be listed in the restoration report
- No error occurs
- You may have intentionally excluded it from the import

### Template Already Has Correct extra_vars

If AAP 2.6 already has the same `extra_vars` content:
- The template is skipped
- Listed as "already current" in the report
- No API call is made

### Different Template IDs

Template IDs will differ between AAP 2.4 and 2.6. This is expected and handled automatically. The restoration report shows both IDs for reference.

## Troubleshooting

### "Preserved data file not found"

You need to run `extract_extra_vars_comments.yml` first.

### "Missing required environment variables"

Set the appropriate AAP24_* or AAP26_* environment variables.

### SSL Certificate Errors

The playbooks default to `validate_certs: false`. If you need SSL validation:
- Edit the playbook
- Change `aap24_validate_certs` or `aap26_validate_certs` to `true`

### API Authentication Fails

Verify:
- Username and password are correct
- User has permissions to read/write job templates
- AAP API is accessible (try curl)

### Template Names Don't Match

If you renamed templates during migration:
1. Edit `preserved_comments/extra_vars_with_comments.json`
2. Update the "name" field to match the new name in AAP 2.6
3. Re-run the restore playbook

## Example extra_vars with Comments

Here's an example of what gets preserved:

```yaml
# ==================================================
# Server Patching Extra Variables
# ==================================================
#
# target_hosts: Inventory group or host pattern
#   Examples: "webservers", "db*.example.com", "all"
#   Default: all
target_hosts: all

# patch_level: Type of patches to apply
#   Options: "security", "all", "critical"
#   Default: security
patch_level: security

# reboot_required: Whether to reboot after patching
#   Options: true, false
#   Default: false
#   WARNING: Setting to true will cause downtime!
reboot_required: false

# notification_email: Email for completion notification
#   Contact: ops-team@example.com
notification_email: ops-team@example.com
```

## Best Practices

1. **Always run extraction before export** - You can't recover comments after the filetree export strips them

2. **Version control the preserved data** - Commit the `preserved_comments/` directory to git

3. **Use dry-run first** - Always preview changes before applying

4. **Document your templates** - Use this as an opportunity to improve your extra_vars documentation

5. **Backup before restore** - Take a backup of AAP 2.6 before running the restore

## Limitations

- Only preserves comments in `extra_vars`, not in other YAML fields
- Templates must have the same name in both systems
- Requires API access to both AAP 2.4 and 2.6
- Does not preserve comments in workflow extra_vars (separate process needed)

## Future Enhancements

Possible improvements for this process:

- Support for workflow job template extra_vars
- Template matching by multiple fields (not just name)
- Automatic detection of renamed templates
- Integration into the filetree export/import role itself

## Support

For issues or questions:
- Review the extraction_report.md and restoration_report.md
- Check AAP API logs for authentication/permission errors
- Verify network connectivity to both AAP instances

## License

This solution is provided as-is for use with Red Hat Ansible Automation Platform.
