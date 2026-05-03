# Vault

Demonstrates using Ansible Vault to encrypt sensitive variables and consume them in playbooks.

## Files

### `vault1.yml`
An Ansible Vault-encrypted variable file containing sensitive values (e.g., `thing1_key`, `thing2_key`). Encrypted with `ansible-vault encrypt`.

### `vault2.yml`
A second encrypted variable file.

### `use_vault.yml`
Playbook that loads `vault1.yml` via `vars_files` and prints the decrypted values. Demonstrates that vaulted variables are transparently decrypted when the vault password is provided.

## Usage

```bash
# Encrypt a file
ansible-vault encrypt vault1.yml

# Run the playbook with vault password
ansible-playbook use_vault.yml --ask-vault-pass
# or
ansible-playbook use_vault.yml --vault-password-file ~/.vault_pass
```
