# MS Azure Key Vault Examples

Comprehensive examples for interacting with Azure Key Vault from Ansible — both reading and writing secrets.

## Playbooks

### `get_secret_from_vault.yml`
Retrieves a named secret from Azure Key Vault using the `azure.azcollection` collection. Sets up Azure authentication via environment variables, queries Key Vault metadata, then fetches the secret value by vault URI.

### `create_kv_secret.yml`
Creates a new secret in Azure Key Vault. Authenticates using Azure service principal environment variables (`AZURE_CLIENT_ID`, `AZURE_SECRET`, `AZURE_TENANT`, `AZURE_SUBSCRIPTION_ID`) and creates a secret (e.g., `adminPassword`) in the specified vault.

### `setup.yml`
Variable definitions file for Azure Key Vault credential type configuration — input field schemas and injector mappings for use in AAP credential types.

## Required Variables
| Variable | Description |
|----------|-------------|
| `AZURE_CLIENT_ID` | Service principal client ID |
| `AZURE_SECRET` | Service principal secret |
| `AZURE_TENANT` | Azure tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `vault_url` | Azure Key Vault URL |
| `secret_name` | Name of the secret to read/write |

## Requirements
- `azure.azcollection` collection
- Python Azure SDK libraries (`pip install azure-keyvault-secrets azure-identity`)

## See Also
- [`Azure_Key_Vault_examples/`](../Azure_Key_Vault_examples/) — simpler read-only example
