# Windows Certificate Authentication Architecture for Ansible

## 1. Summary of the Purpose

The primary objective of this architecture is to establish a highly secure, password-less, and scalable remote management framework for Windows systems within an enterprise environment. By transitioning away from traditional password-based authentication and high-risk protocols like Credential Security Support Provider (CredSSP), the organization can significantly reduce its attack surface.

Specifically, we are implementing Mutual TLS (mTLS) Certificate Authentication over Windows Remote Management (WinRM) and the PowerShell Remoting Protocol (PSRP). This ensures that:

- **Identity is strongly authenticated**: Both the client (Ansible Automation Platform) and the target Windows servers cryptographically prove their identities using X.509 certificates.
- **Traffic is encrypted by default**: All remote management traffic is encapsulated within an HTTPS tunnel (Port 5986), protecting sensitive data and command execution from network interception.
- **Credential dumping risks are mitigated**: Unlike CredSSP, which delegates raw credentials from the client to the target machine over the network (creating a "double-hop" vulnerability), certificate authentication never transmits a password at all — the client presents only a certificate. The target host still uses a real Windows account password internally to build the resulting logon session (see Phase 3, step 4), but that password is never known to, sent by, or stored in AAP.
- **Automation is seamless**: Ansible Automation Platform (AAP) can securely inject Client Certificates dynamically at runtime, eliminating the need to store any Windows account passwords in AAP credentials.

### Architecture Comparison: CredSSP vs. Windows Certificates

| Feature | CredSSP | Windows Certificates (HTTPS) |
|---|---|---|
| Primary Purpose | Credential delegation across multi-hop remote sessions. | Encrypted transport and PKI-based identity authentication. |
| Security Profile | Higher Risk: Target server gets delegable credentials (credential dumping risk). | Lower Risk: Uses X.509 PKI trust; raw credentials are never forwarded to the target host. |
| Network Port | HTTP (5985) or HTTPS (5986) | HTTPS (5986) strictly enforced. |

### WinRM Authentication Methods Comparison

Certificate authentication is one of five authentication options WinRM supports. The table below shows why it was chosen over the alternatives for this architecture: it supports local accounts (matching the local-account mapping model used in Phase 3) without enabling credential delegation, unlike NTLM and CredSSP.

| Option | Local Accounts | Active Directory Accounts | Credential Delegation | HTTP Encryption |
|---|---|---|---|---|
| Basic | Yes | No | No | No |
| Certificate | Yes | No | No | No |
| Kerberos | No | Yes | Yes | Yes |
| NTLM | Yes | Yes | No | Yes |
| CredSSP | Yes | Yes | Yes | Yes |

Certificate authentication's "No" on Credential Delegation is the key security property here: there is no delegable credential for a compromised target to reuse against other hosts, which is exactly the "double-hop" risk CredSSP carries. Its "No" on Active Directory Accounts is why this architecture maps certificates to local accounts (Phase 3, step 4) rather than domain accounts.

## 2. Steps to Achieve the Outlined Goals

To achieve end-to-end implementation of this architecture, the following structured phases must be executed. This covers the underlying PKI infrastructure, endpoint configuration, client certificate generation, and automation platform integration.

https://access.redhat.com/solutions/7099480

### Phase 1: Deploy Active Directory Certificate Services (AD CS)

To establish implicit trust across the domain, an Enterprise Root CA must be configured. This ensures that any certificate issued by the CA is automatically trusted by all domain-joined target computers via Active Directory's automated distribution to the Trusted Root Certification Authorities store.

```yaml
- name: Deploy AD CS Enterprise Root CA
  hosts: ca_servers
  tasks:
    - name: Install AD CS Server Feature and Management Tools
      ansible.windows.win_feature:
        name:
          - ADCS-Cert-Authority
          - ADCS-Web-Enrollment
          - RSAT-ADCS-Mgmt
        state: present
        include_management_tools: true

    - name: Configure Enterprise Root Certificate Authority
      ansible.windows.win_powershell:
        script: |
          Import-Module ADCSDeployment
          Install-AdcsCertificationAuthority `
              -CAType EnterpriseRootCA `
              -CryptoProviderName "RSA#Microsoft Software Key Storage Provider" `
              -KeyLength 4096 `
              -HashAlgorithmName SHA256 `
              -ValidityPeriod Years `
              -ValidityPeriodUnits 10 -Force
```

### Phase 2: Configure Target Windows Systems

Each target Windows system must be configured to expose an HTTPS WinRM listener on Port 5986, backed by a valid Server Authentication certificate. Furthermore, the WinRM service must be instructed to accept Certificate Authentication payloads.

```yaml
- name: Configure WinRM HTTPS and Certificate Authentication
  hosts: win_servers
  tasks:
    - name: Allow inbound WinRM HTTPS traffic on port 5986
      ansible.windows.win_firewall_rule:
        name: WinRM-HTTPS-In
        localport: 5986
        protocol: tcp
        action: allow
        direction: in
        state: present
        enabled: yes

    - name: Enable certificate authentication in WinRM service
      ansible.windows.win_powershell:
        script: |
          Set-Item -Path WSMan:\localhost\Service\Auth\Certificate -Value $true

          # Logic to bind the Server Authentication cert to the HTTPS listener
          $cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.EnhancedKeyUsageList.EnhancedKeyUsage.Value -contains "1.3.6.1.5.5.7.3.1" } | Select-Object -First 1
          New-WSManInstance -ResourceURI winrm/config/Listener -SelectorSet @{Address="*"; Transport="HTTPS"} -ValueSet @{Hostname=$env:COMPUTERNAME; CertificateThumbprint=$cert.Thumbprint}
```

### Phase 3: One-Time AAP Custom Credential Type Setup

Before any certificate material can be pushed into AAP, a Custom Credential Type must exist that accepts the client certificate and key as multi-line PEM strings and injects them as PSRP connection variables. This is a one-time setup step; the certificate itself is generated and registered in Phase 4.

1. Install the `pypsrp` library into the Execution Environment.
2. Create an AAP Custom Credential Type (e.g. `WinRM Client Certificate`) with secret, multi-line input fields `client_certificate_pem` and `client_certificate_key_pem`.
3. Configure the credential injector to write these inputs to temporary files and inject the following extra variables:

   ```yaml
   ansible_connection: psrp
   ansible_port: 5986
   ansible_psrp_auth: certificate
   ansible_psrp_certificate_pem: "{{ tower.filename.client_certificate_pem }}"
   ansible_psrp_certificate_key_pem: "{{ tower.filename.client_certificate_key_pem }}"
   ```

   > The `tower.filename.<field>` namespace is used by file-based custom credential injectors; confirm the exact variable name against your AAP version's Custom Credential Type documentation before relying on it.

4. Map the Certificate Subject and Issuer in the Windows WSMan IssuerMapping (on each target host) to a valid local administrator account.

   This mapping is what lets a target host translate "a client presented a certificate with this Subject, signed by this Issuer" into "log this session in as local account X." Map to a dedicated local automation account rather than the built-in `Administrator`, so the mapping can be disabled or rotated independently of that account.

   **The mapping account's password is generated fresh, in memory, on every run of this playbook, and is never persisted anywhere** — not in AAP's Vault, not as a credential object, not on disk. AAP only needs the certificate to use this connection; it never needs the mapping account's password to do so, since the password is used purely internally by the target host to build the Windows logon session once the certificate has matched. Because `win_user` *sets* the password rather than verifying a prior value, the playbook never needs to know what the password was before — every run mints a new one for that host and re-applies the mapping to match. This gives each host a unique, unknown-to-AAP password with no rotation workflow beyond "run this playbook again." See [`wsman_mapping_credential_options.md`](./wsman_mapping_credential_options.md) for the full security tradeoff analysis and the alternatives considered (a shared static password, a domain account rotated via an AD-integrated AAP workflow, and a Windows LAPS-managed account).

   Run this against `win_servers` after the client certificate has been generated in Phase 4, since it needs the resulting `client_cert_subject`:

   ```yaml
   - name: Map the AAP client certificate to a local automation account
     hosts: win_servers
     vars:
       client_cert_subject: "CN=aap-winrm-client"
       ca_common_name: "ExampleCorp-Root-CA"
       automation_account_name: "aap_winrm_svc"

     tasks:
       - name: Generate an ephemeral, per-host mapping-account password (never persisted)
         ansible.builtin.set_fact:
           automation_account_password: "{{ lookup('password', '/dev/null chars=ascii_letters,digits length=32') }}"
         no_log: true

       - name: Ensure the local automation account exists
         ansible.windows.win_user:
           name: "{{ automation_account_name }}"
           password: "{{ automation_account_password }}"
           password_never_expires: true
           user_cannot_change_password: true
           state: present
         no_log: true

       - name: Add the automation account to local Administrators
         ansible.windows.win_group_membership:
           name: Administrators
           members:
             - "{{ automation_account_name }}"
           state: present

       - name: Create or refresh the WSMan ClientCertificate mapping
         ansible.windows.win_powershell:
           script: |
             $issuerCert = Get-ChildItem Cert:\LocalMachine\Root |
               Where-Object { $_.Subject -like "*{{ ca_common_name }}*" } |
               Select-Object -First 1
             if (-not $issuerCert) {
               throw "Enterprise Root CA certificate '{{ ca_common_name }}' not found in the Trusted Root store."
             }

             $securePwd = ConvertTo-SecureString -String "{{ automation_account_password }}" -AsPlainText -Force
             $credential = New-Object System.Management.Automation.PSCredential(
               "{{ automation_account_name }}", $securePwd)

             $existing = Get-ChildItem WSMan:\localhost\ClientCertificate | Where-Object {
               $_.Subject -eq "{{ client_cert_subject }}" -and $_.Issuer -eq $issuerCert.Thumbprint
             }
             if ($existing) {
               $existing | Remove-Item -Force
             }

             New-Item -Path WSMan:\localhost\ClientCertificate `
               -Subject "{{ client_cert_subject }}" `
               -URI * `
               -Issuer $issuerCert.Thumbprint `
               -Credential $credential `
               -Force | Out-Null
           # ClientCertificate mappings don't support Ansible's native
           # idempotent change detection; the existing-mapping check above
           # keeps repeated runs from erroring or leaving stale duplicates.
         no_log: true
   ```

   The `password` lookup with `/dev/null` as its source path generates a random value without writing it to a reusable file on disk. `no_log: true` on every task that touches `automation_account_password` is required, not optional — without it, the generated value would appear in AAP's job stdout and event data, which would defeat the entire point of not persisting it. Because `win_powershell` can't natively report "changed" for this provider, wrap the mapping logic behind a `check`/`Remove-Item`-then-recreate pattern (shown above) rather than relying on the module's own change tracking.

### Phase 4: Generate, Sign, and Register the Client Certificate (Configuration as Code)

This playbook performs the full certificate lifecycle end-to-end as a single AAP job:

1. Generates the CSR and private key on the CA host itself and submits it to the local Enterprise CA for signing, so the certificate is properly chained and carries the Client Authentication EKU (`1.3.6.1.5.5.7.3.2`) and a real Subject for Issuer Mapping.
2. Exports the signed certificate and key as a password-protected PFX and pulls it into the Execution Environment.
3. Converts the PFX to PEM and pushes the values into the `WinRM Client Certificate` credential defined in Phase 3 using `ansible.controller.credential` — configuration as code, the same pattern used in `controller_export_import/`.
4. Deletes every intermediate artifact from both the CA host and the Execution Environment, so the only durable copy of the key material is the encrypted credential inside AAP.

Re-running this job template is how the certificate gets rotated.

```yaml
- name: Generate and sign the AAP WinRM client certificate on the CA host
  hosts: ca_servers
  vars:
    client_cert_subject: "CN=aap-winrm-client"
    ca_config: "{{ inventory_hostname }}\\ExampleCorp-Root-CA"
    pfx_export_password: "{{ vaulted_pfx_export_password }}"
    work_dir: "C:\\Windows\\Temp\\aap_winrm_client"

  tasks:
    - name: Create working directory for certificate request artifacts
      ansible.windows.win_file:
        path: "{{ work_dir }}"
        state: directory

    - name: Render certreq INF template for a Client Authentication CSR
      ansible.windows.win_template:
        src: aap_winrm_client.inf.j2
        dest: "{{ work_dir }}\\request.inf"

    - name: Generate the CSR and private key
      ansible.windows.win_command: >
        certreq -new "{{ work_dir }}\request.inf" "{{ work_dir }}\request.csr"

    - name: Submit the CSR to the local Enterprise CA for signing
      ansible.windows.win_command: >
        certreq -submit -config "{{ ca_config }}" "{{ work_dir }}\request.csr" "{{ work_dir }}\signed.cer"

    - name: Accept the signed certificate into the local machine store
      ansible.windows.win_command: >
        certreq -accept "{{ work_dir }}\signed.cer"

    - name: Locate the issued certificate by Subject
      ansible.windows.win_powershell:
        script: |
          $cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Subject -eq "{{ client_cert_subject }}" } | Sort-Object NotBefore -Descending | Select-Object -First 1
          $result.thumbprint = $cert.Thumbprint
      register: issued_cert

    - name: Export the certificate and private key as a password-protected PFX
      ansible.windows.win_powershell:
        script: |
          $securePwd = ConvertTo-SecureString -String "{{ pfx_export_password }}" -Force -AsPlainText
          $cert = Get-Item "Cert:\LocalMachine\My\{{ issued_cert.output.thumbprint }}"
          Export-PfxCertificate -Cert $cert -FilePath "{{ work_dir }}\aap_winrm_client.pfx" -Password $securePwd

    - name: Fetch the signed PFX into the Execution Environment
      ansible.builtin.fetch:
        src: "{{ work_dir }}\\aap_winrm_client.pfx"
        dest: "/tmp/aap_winrm_client.pfx"
        flat: true

    - name: Remove CSR, certificate, and PFX artifacts from the CA host
      ansible.windows.win_file:
        path: "{{ work_dir }}"
        state: absent

- name: Convert the certificate to PEM and register it in AAP
  hosts: localhost
  connection: local
  gather_facts: false
  vars:
    pfx_export_password: "{{ vaulted_pfx_export_password }}"

  tasks:
    - name: Extract the client certificate as PEM
      ansible.builtin.command: >
        openssl pkcs12 -in /tmp/aap_winrm_client.pfx -clcerts -nokeys
        -passin env:PFX_EXPORT_PASSWORD -out /tmp/aap_winrm_client_cert.pem
      environment:
        PFX_EXPORT_PASSWORD: "{{ pfx_export_password }}"
      no_log: true

    - name: Extract the unencrypted private key as PEM
      ansible.builtin.command: >
        openssl pkcs12 -in /tmp/aap_winrm_client.pfx -nocerts -nodes
        -passin env:PFX_EXPORT_PASSWORD -out /tmp/aap_winrm_client_key.pem
      environment:
        PFX_EXPORT_PASSWORD: "{{ pfx_export_password }}"
      no_log: true

    - name: Read the PEM cert and key back into variables
      ansible.builtin.slurp:
        src: "{{ item }}"
      loop:
        - /tmp/aap_winrm_client_cert.pem
        - /tmp/aap_winrm_client_key.pem
      register: pem_files
      no_log: true

    - name: Register/update the credential in AAP (configuration as code)
      ansible.controller.credential:
        name: "AAP WinRM Client Certificate"
        organization: "Default"
        credential_type: "WinRM Client Certificate"
        inputs:
          client_certificate_pem: "{{ pem_files.results[0].content | b64decode }}"
          client_certificate_key_pem: "{{ pem_files.results[1].content | b64decode }}"
        state: present
      no_log: true
      # controller_host/controller_username/controller_password are read from the
      # CONTROLLER_HOST/CONTROLLER_USERNAME/CONTROLLER_PASSWORD environment variables
      # injected into the job -- the same pattern used in controller_export_import/.

    - name: Remove PFX and PEM artifacts from the Execution Environment
      ansible.builtin.file:
        path: "{{ item }}"
        state: absent
      loop:
        - /tmp/aap_winrm_client.pfx
        - /tmp/aap_winrm_client_cert.pem
        - /tmp/aap_winrm_client_key.pem
```

`aap_winrm_client.inf.j2` (templates directory):

```ini
[Version]
Signature="$Windows NT$"

[NewRequest]
Subject = "{{ client_cert_subject }}"
KeySpec = 1
KeyLength = 2048
Exportable = TRUE
MachineKeySet = TRUE
SMIME = FALSE
RequestType = PKCS10
KeyUsage = 0xa0
ProviderName = "Microsoft RSA SChannel Cryptographic Provider"
ProviderType = 12

[EnhancedKeyUsageExtension]
OID = 1.3.6.1.5.5.7.3.2
```

`pfx_export_password` must come from an Ansible Vault-encrypted variable, never plaintext. Because the Execution Environment's filesystem is destroyed at job completion, none of the intermediate PFX/PEM files persist beyond the run — the only durable copy of the key material lives inside the encrypted AAP credential.

Completion of these four phases achieves full, scalable deployment of encrypted, password-less Windows automation.
