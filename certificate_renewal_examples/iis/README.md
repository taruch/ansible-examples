# IIS Certificate Renewal

Renews an SSL certificate on a Windows IIS server by importing a renewed
`.pfx` into the LocalMachine certificate store and re-binding the site to the
new thumbprint. No service restart required — the rebind is the cutover.

## What it does

1. Stages the renewed `.pfx` on the IIS host with a date-versioned filename.
2. Imports the cert into `LocalMachine\My` (the Web Hosting / Personal store
   IIS reads from), capturing the resulting thumbprint.
3. Updates the HTTPS binding on the target site to reference the new
   thumbprint. The previous cert stays in the store so rollback is trivial.
4. Reads the live binding back with PowerShell and asserts the served
   thumbprint matches what was just imported.
5. Cleans up the staged `.pfx` (the cert lives in the store now, not on disk).

## Rollback

The previous cert is still in `LocalMachine\My`. To roll back, look up its
thumbprint and re-run the rebind step against it:

```powershell
Get-ChildItem Cert:\LocalMachine\My | Where-Object Subject -like "*example.com*"
```

```yaml
- name: Roll back to previous cert
  community.windows.win_iis_webbinding:
    name: "Default Web Site"
    protocol: https
    port: 443
    host_header: www.example.com
    certificate_hash: "OLD_THUMBPRINT_HERE"
    certificate_store_name: My
    state: present
```

## Layout

```
iis/
├── README.md
├── renew_iis_cert.yml
├── requirements.yml
├── files/
│   └── wildcard_example_com.pfx     # not committed
└── inventory/
    ├── hosts.yml
    └── host_vars/
        └── iis01.example.com.yml
```

## Prerequisites

```bash
ansible-galaxy collection install -r requirements.yml
```

Place the renewed PFX bundle under `files/`:

```
files/wildcard_example_com.pfx
```

Encrypt the PFX password with ansible-vault (or use an AAP Vault credential):

```bash
ansible-vault encrypt_string 'p@ssword' --name vault_pfx_password
```

## Usage

```bash
ansible-playbook -i inventory/hosts.yml renew_iis_cert.yml --ask-vault-pass
```

Targeting a different site or SNI host:

```bash
ansible-playbook -i inventory/hosts.yml renew_iis_cert.yml \
  -e site_name='Default Web Site' \
  -e binding_host_header=api.example.com
```

## AAP / Controller

Use a **Machine** credential for WinRM and a **Vault** credential for the PFX
password. A surveyed `cert_name`, `site_name`, and `binding_host_header` make
the same template reusable across every IIS cert you manage.

## Connection notes

The sample inventory uses Kerberos + WinRM on 5986. Adjust
`ansible_winrm_transport` (e.g. `ntlm`, `credssp`) to match your environment.
