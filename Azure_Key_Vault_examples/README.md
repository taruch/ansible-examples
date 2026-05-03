# Azure Key Vault Examples

Demonstrates retrieving secrets from Azure Key Vault using Ansible lookup plugins.

## Playbooks

### `get_secret_from_vault.yml`
Retrieves a secret value from Azure Key Vault using the `azure.azcollection` lookup plugin. Authenticates with Azure service principal credentials and fetches a named secret by vault URL.

## Requirements
- `azure.azcollection` collection
- Azure service principal with Key Vault read access (`AZURE_CLIENT_ID`, `AZURE_SECRET`, `AZURE_TENANT`, `AZURE_SUBSCRIPTION_ID`)
- Target Key Vault URL and secret name

## See Also
- [`MS_Azure_Key_Vault_examples/`](../MS_Azure_Key_Vault_examples/) — extended examples including secret creation
