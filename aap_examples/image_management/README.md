# AAP Image Management Examples

Playbooks for managing Execution Environment images in Ansible Automation Platform 2.6.

## tag_execution_environment.yml

Tags container images in AAP's Private Automation Hub using the OCI Registry API.

**Key Feature:** Works from any Execution Environment - no podman/docker required!

### How It Works

This playbook uses the OCI Distribution Specification (Registry HTTP API) to:
1. Authenticate with the container registry
2. Download the manifest for the source tag
3. Upload the same manifest with a new tag reference

This creates a new tag pointing to the same image layers - no image data is copied.

### Prerequisites

**None!** Uses only `ansible.builtin.uri` which is included in ansible-core.

Works with:
- Private Automation Hub
- Red Hat Quay
- Harbor
- Docker Registry v2
- Any OCI-compliant registry

### Usage

#### Basic Usage

```bash
ansible-playbook tag_execution_environment.yml \
  -e image_name=ee-minimal-rhel9 \
  -e source_tag=latest \
  -e new_tag=1.0.0
```

#### With Custom Registry

```bash
ansible-playbook tag_execution_environment.yml \
  -e registry=hub.example.com \
  -e image_name=custom-ee \
  -e source_tag=2.0.0 \
  -e new_tag=production
```

#### Run from AAP Job Template

1. Create a job template in AAP
2. Set the playbook path
3. Add variables:
   - `image_name`: ee-minimal-rhel9
   - `source_tag`: latest
   - `new_tag`: 1.0.0
4. Add credentials (or use env vars)
5. Launch!

### Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `image_name` | Yes | `ee-minimal-rhel9` | Name of the EE image (repository name) |
| `source_tag` | Yes | `latest` | Existing tag to copy from |
| `new_tag` | Yes | `1.0.0` | New tag to create |
| `registry` | No | `{{ ah_host }}` | Container registry hostname |
| `ah_host` | No | `automationhub.example.com` | Automation Hub hostname |
| `ah_username` | No | `admin` | Registry username |
| `ah_password` | Yes | (from env `AH_PASSWORD`) | Registry password |
| `ah_validate_certs` | No | `false` | Validate SSL certificates |

### Environment Variables

```bash
export AH_HOST=automationhub.example.com
export AH_USERNAME=admin
export AH_PASSWORD=your_password
export AH_VERIFY_SSL=false  # or 'true' for production
```

### Examples

#### Tag latest as a version

```bash
ansible-playbook tag_execution_environment.yml \
  -e image_name=ee-supported-rhel9 \
  -e source_tag=latest \
  -e new_tag=2.16.0
```

#### Promote staging to production

```bash
ansible-playbook tag_execution_environment.yml \
  -e image_name=custom-ee \
  -e source_tag=staging \
  -e new_tag=production
```

#### Create multiple tags

```bash
# Tag as both 'stable' and 'v1.0.0'
ansible-playbook tag_execution_environment.yml \
  -e image_name=my-ee \
  -e source_tag=latest \
  -e new_tag=stable

ansible-playbook tag_execution_environment.yml \
  -e image_name=my-ee \
  -e source_tag=latest \
  -e new_tag=v1.0.0
```

### Troubleshooting

#### Authentication Failures

```
FAILED: HTTP Error 401: Unauthorized
```

**Solution:** Check username/password and ensure the account has push access to the repository.

#### Tag Not Found

```
FAILED: HTTP Error 404: Not Found (source tag)
```

**Solution:** Verify the source tag exists:
```bash
curl -u admin:password https://automationhub.example.com/v2/ee-minimal-rhel9/tags/list
```

#### Certificate Verification Failed

```
FAILED: certificate verify failed
```

**Solution:** Either:
- Set `ah_validate_certs: false` (dev/lab only)
- Add the CA cert to the EE's trust store
- Set `AH_VERIFY_SSL=false`

#### Registry API Not Supported

Some registries may require different API endpoints. Check registry documentation.

### Registry API Endpoints Used

- `GET /v2/token` - Authentication (optional, registry-dependent)
- `GET /v2/{name}/manifests/{tag}` - Fetch manifest
- `PUT /v2/{name}/manifests/{tag}` - Create new tag
- `HEAD /v2/{name}/manifests/{tag}` - Verify tag exists

### Notes

- **No image data is transferred** - only the manifest (metadata) is copied
- **Atomic operation** - the new tag is created instantly
- **Same digest** - both tags point to the exact same image layers
- **Space efficient** - no additional storage used
- **Works in any EE** - no special tools or packages required

### AAP Integration

This playbook can be used in AAP workflows to:
- Tag images after successful builds
- Promote images through environments (dev → staging → prod)
- Version EE images as part of CI/CD
- Create backup tags before updates

Example workflow:
1. Build EE → tags as `latest`
2. Run tests → if pass, tag as `staging`
3. Manual approval → tag as `production`
