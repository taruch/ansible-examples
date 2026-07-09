# Granite Model Deployment for AAP Ansible Intelligent Assistant

This playbook deploys IBM's Granite model on RHEL 9 using Ollama for integration with Ansible Automation Platform 2.7's Ansible Intelligent Assistant feature.

## Overview

IBM Granite models are open-source LLMs specifically designed for enterprise use cases, including code generation and automation. This playbook sets up Ollama (a lightweight LLM runtime) with Granite models on RHEL 9.

## Prerequisites

### System Requirements
- **OS**: RHEL 9.x
- **Memory**: Minimum 16GB RAM (32GB recommended for granite3.1-dense:8b)
- **Disk**: Minimum 50GB free space
- **CPU**: x86_64 architecture with AVX support
- **Network**: Internet access for model download

### AAP Requirements
- Ansible Automation Platform 2.7 or later
- Administrative access to AAP settings

## Available Granite Models

| Model | Size | Memory Required | Use Case |
|-------|------|----------------|----------|
| `granite3.1-dense:2b` | 2B params | 8GB+ | Lightweight, fast responses |
| `granite3.1-dense:8b` | 8B params | 16GB+ | **Recommended** - Best balance of performance/quality |
| `granite3.1-moe:3b` | 3B params | 12GB+ | Mixture of Experts architecture |

## Quick Start

### 1. Deploy the Model

```bash
ansible-playbook deploy_granite_model.yml -i inventory
```

### 2. Test the Deployment

Run verification and test prompts using the AAP job template:

```bash
# Setup the job template in AAP
ansible-playbook setup_aap_job_template.yml

# Or test manually from command line
ansible-playbook test_granite_model.yml \
  -e "run_verification=true" \
  -e "run_test_prompts=true"
```

See [AAP_JOB_TEMPLATE_SETUP.md](AAP_JOB_TEMPLATE_SETUP.md) for complete testing instructions.

## Usage

### Basic Deployment

```bash
# Deploy with default settings (granite3.1-dense:8b)
ansible-playbook deploy_granite_model.yml -i inventory

# Deploy a different model
ansible-playbook deploy_granite_model.yml -i inventory \
  -e "granite_model=granite3.1-dense:2b"
```

### Using with Execution Environment

```bash
ansible-navigator run -mstdout deploy_granite_model.yml \
  --inventory inventory \
  --eei=quay.io/ansible/creator-ee:latest
```

### Custom Configuration

```bash
ansible-playbook deploy_granite_model.yml -i inventory \
  -e "granite_model=granite3.1-dense:8b" \
  -e "ollama_host=0.0.0.0" \
  -e "ollama_port=11434"
```

## Inventory Example

Create an `inventory` file:

```ini
[granite_servers]
rhel9-ai.example.com ansible_user=ec2-user ansible_become=true
```

Or use AAP inventory with appropriate host groups.

## Post-Deployment Configuration

### Configure AAP 2.7 Ansible Intelligent Assistant

1. **Log into AAP Web UI** as an administrator

2. **Navigate to Settings**:
   - Click **Administration** → **Settings**
   - Select **AI** category

3. **Configure Model Provider**:
   - **Model Provider**: Self-hosted
   - **API URL**: `http://<granite-server-ip>:11434`
   - **Model Name**: `granite3.1-dense:8b` (or your chosen model)
   - **API Key**: Leave blank (not required for Ollama)
   - **Verify SSL**: Disabled (for non-TLS setup)

4. **Test the Connection**:
   - Click **Test** to verify AAP can reach the model
   - You should see a successful connection message

5. **Enable for Users**:
   - Navigate to **Access** → **Users**
   - Edit user permissions to grant AI assistant access

### Automated Testing with AAP Survey

The easiest way to test your deployment is using the AAP job template with survey:

1. **Setup the job template** (one-time):
   ```bash
   ansible-playbook setup_aap_job_template.yml
   ```

2. **Launch from AAP UI**:
   - Go to **Resources > Templates**
   - Click **Launch** on "Granite Model - Test and Verify"
   - Fill out the survey with your test parameters
   - Click **Launch**

3. **Or run from command line**:
   ```bash
   ansible-playbook test_granite_model.yml \
     -e "run_verification=true" \
     -e "run_test_prompts=true" \
     -e "custom_prompt='Write a task to create a user named devops'"
   ```

See [AAP_JOB_TEMPLATE_SETUP.md](AAP_JOB_TEMPLATE_SETUP.md) for complete documentation.

### Manual Testing

Test the model directly from the command line:

```bash
# Simple test
curl http://localhost:11434/api/generate -d '{
  "model": "granite3.1-dense:8b",
  "prompt": "Write an Ansible task to install nginx on RHEL",
  "stream": false
}'

# List available models
curl http://localhost:11434/api/tags

# Or use the included verification script
bash verify_deployment.sh
```

### Using Ollama CLI

```bash
# Interactive chat
ollama run granite3.1-dense:8b

# One-shot question
ollama run granite3.1-dense:8b "Explain Ansible roles"

# List models
ollama list

# Remove a model
ollama rm granite3.1-dense:2b

# Pull additional models
ollama pull granite3.1-moe:3b
```

## Architecture

```
┌─────────────────────────────────────┐
│   Ansible Automation Platform 2.7   │
│   (Ansible Intelligent Assistant)   │
└─────────────┬───────────────────────┘
              │ HTTP API calls
              │ (port 11434)
              ▼
┌─────────────────────────────────────┐
│      RHEL 9 Server (This host)      │
│  ┌───────────────────────────────┐  │
│  │     Ollama Service            │  │
│  │  (systemd managed)            │  │
│  │                               │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  Granite Model          │  │  │
│  │  │  granite3.1-dense:8b    │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
│                                     │
│  Models stored in:                  │
│  /usr/share/ollama/.ollama/models   │
└─────────────────────────────────────┘
```

## Troubleshooting

### Service Issues

```bash
# Check Ollama service status
systemctl status ollama

# View logs
journalctl -u ollama -f

# Restart service
systemctl restart ollama
```

### Model Download Issues

```bash
# Check disk space
df -h /usr/share/ollama

# Retry model pull
ollama pull granite3.1-dense:8b

# Check Ollama version
ollama --version
```

### Performance Issues

If the model is slow or unresponsive:

1. **Check memory usage**: `free -h`
2. **Consider a smaller model**: Switch to `granite3.1-dense:2b`
3. **Increase system resources**: Add more RAM if possible
4. **Check CPU**: Granite models benefit from AVX2 instruction sets

### Firewall Issues

```bash
# Check if port is open
firewall-cmd --list-ports

# Manually add port if needed
firewall-cmd --permanent --add-port=11434/tcp
firewall-cmd --reload
```

### AAP Connection Issues

```bash
# Test connectivity from AAP controller
curl -v http://<granite-server>:11434/api/tags

# Check SELinux (if enabled)
ausearch -m avc -ts recent

# Temporarily set permissive (for testing only)
setenforce 0
```

## Security Considerations

### Production Deployment

For production use, consider:

1. **TLS/SSL**: Configure reverse proxy (nginx/Apache) with TLS
2. **Authentication**: Implement API authentication layer
3. **Network**: Restrict access via firewall rules
4. **SELinux**: Keep enabled and configure appropriate policies
5. **Resource Limits**: Use systemd resource controls

### Example: Nginx Reverse Proxy with TLS

```nginx
server {
    listen 443 ssl;
    server_name granite-api.example.com;
    
    ssl_certificate /etc/pki/tls/certs/granite.crt;
    ssl_certificate_key /etc/pki/tls/private/granite.key;
    
    location / {
        proxy_pass http://127.0.0.1:11434;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Updating Models

To update to a newer version of Granite:

```bash
# Pull the latest version
ollama pull granite3.1-dense:8b

# Remove old version (if needed)
ollama list  # Find old version
ollama rm granite3.1-dense:8b-old
```

## Uninstallation

```bash
# Stop and disable service
systemctl stop ollama
systemctl disable ollama

# Remove service file
rm /etc/systemd/system/ollama.service
systemctl daemon-reload

# Remove Ollama binary
rm /usr/local/bin/ollama

# Remove models and data
rm -rf /usr/share/ollama

# Remove user
userdel ollama
```

## Additional Resources

- [IBM Granite Models](https://github.com/ibm-granite/granite-code-models)
- [Ollama Documentation](https://github.com/ollama/ollama)
- [AAP 2.7 Documentation](https://access.redhat.com/documentation/en-us/red_hat_ansible_automation_platform/2.7)
- [Ansible Intelligent Assistant Guide](https://access.redhat.com/documentation/en-us/red_hat_ansible_automation_platform/2.7/html/using_ansible_ai_assistant)

## Support

For issues related to:
- **Playbook**: Open an issue in this repository
- **Ollama**: Visit [Ollama GitHub](https://github.com/ollama/ollama/issues)
- **Granite Models**: Visit [IBM Granite GitHub](https://github.com/ibm-granite/granite-code-models/issues)
- **AAP**: Contact Red Hat Support
